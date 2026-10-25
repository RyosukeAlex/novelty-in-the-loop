"""B（最近傍距離）の予測力が、母集団サイズでどう変わるかを測る。

なぜ必要か（docs/engine-v0.md §10-5）:
  B_strict の母集団は「対象が引用した論文＋対象を引用した論文」の集合で、
  ML 分野に偏った部分集合（10.9〜15.5 万本）にすぎない。
  条件B（AI Scientist の最近傍チェック）は本来 OpenAlex 全体（約 1.2 億本）を
  検索する設定なので、**母集団をさらに広げたら B はもっと強くなる可能性がある。**
  これは提案手法に不利な方向の課題だが、放置すると第4章の主張が崩れる。

設計:
  母配当を出版年以前に限ったうえで、その中からランダムに N 本を取って B を計算する。
  N を変えて予測力の飽和曲線を描き、N = 1.2 億への外挿を見る。
  サブセットは入れ子（N1 ⊂ N2 ⊂ …）にして 1 パスで全サイズの最近傍を同時に取る。
  シードを 3 本振って平均する。
"""

import csv
import json
import sys

import numpy as np
from scipy.stats import spearmanr
from sklearn.linear_model import Ridge
from sklearn.model_selection import KFold, cross_val_predict
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

EMB = "data/engine/sciscinet_emb"
VAL = "data/engine/validation.csv"
YEARS = "data/engine/neighbor_years.csv"
SIZES = [2_000, 5_000, 10_000, 25_000, 50_000, 100_000, None]   # None = 全部
SEEDS = [11, 22, 33]
BLOCK = 20_000


def main() -> int:
    vecs = np.load(EMB + ".npy")
    ids = json.load(open(EMB + "_ids.json", encoding="utf-8"))["paperids"]
    pos = {p: i for i, p in enumerate(ids)}
    unit = vecs / np.linalg.norm(vecs, axis=1, keepdims=True)

    yr = np.full(len(ids), -1, dtype=np.int32)
    for r in csv.DictReader(open(YEARS, encoding="utf-8")):
        if r["year"] and r["paperid"] in pos:
            yr[pos[r["paperid"]]] = int(r["year"])

    rows = [r for r in csv.DictReader(open(VAL, encoding="utf-8")) if r["paperid"] in pos]
    def col(k, f=float):
        return np.array([f(r[k]) if r[k] else np.nan for r in rows])

    mv = col("movement")
    n_past, n_future = col("n_past", int), col("n_future", int)
    dis = col("disruption")
    dv = np.array([r["d_valid"] == "true" for r in rows])
    Z = np.column_stack([np.ones(len(rows)), np.log(n_past), np.log(n_future)])
    y_res = mv - Z @ np.linalg.lstsq(Z, mv, rcond=None)[0]

    by_year: dict[int, list[int]] = {}
    for k, r in enumerate(rows):
        by_year.setdefault(int(r["year"]), []).append(k)

    print(f"評価対象 {len(rows)} 本 / シード {len(SEEDS)} 本", flush=True)

    # b_all[seed][size_index] = 各対象論文の B
    b_all = {s: {i: np.full(len(rows), np.nan, dtype=np.float32)
                 for i in range(len(SIZES))} for s in SEEDS}

    for seed in SEEDS:
        rng = np.random.default_rng(seed)
        for y, ks in sorted(by_year.items()):
            pool = np.where((yr > 0) & (yr < y))[0]
            rng.shuffle(pool)
            caps = [len(pool) if n is None else min(n, len(pool)) for n in SIZES]
            tgt = np.array([pos[rows[k]["paperid"]] for k in ks])
            best = np.full((len(SIZES), len(tgt)), -np.inf, dtype=np.float32)

            # 入れ子のサブセットを 1 パスで処理する。
            # ブロックの終端位置が各サイズの上限を超えていなければ、そのサイズの max に含める。
            for s in range(0, len(pool), BLOCK):
                e = min(s + BLOCK, len(pool))
                sim = unit[tgt] @ unit[pool[s:e]].T        # (対象, ブロック)
                for si, cap in enumerate(caps):
                    if s >= cap:
                        continue
                    upto = min(e, cap) - s
                    m = sim[:, :upto].max(axis=1)
                    np.maximum(best[si], m, out=best[si])
            for si in range(len(SIZES)):
                for j, k in enumerate(ks):
                    b_all[seed][si][k] = 1.0 - float(best[si][j])
            print(f"  seed {seed} / {y} 年: 母集団 {len(pool):,} 本 完了", flush=True)

    kf = KFold(n_splits=5, shuffle=True, random_state=42)
    print(f"\n{'母集団 N':>12}{'B の予測力':>13}{'(標準偏差)':>12}{'B × D':>10}{'B の中央値':>12}")
    curve = []
    for si, n in enumerate(SIZES):
        rs, rds, meds = [], [], []
        for seed in SEEDS:
            b = b_all[seed][si]
            pipe = make_pipeline(StandardScaler(), Ridge(alpha=10.0))
            pred = cross_val_predict(pipe, b.reshape(-1, 1), y_res, cv=kf, n_jobs=-1)
            rs.append(spearmanr(pred, y_res).statistic)
            rds.append(spearmanr(b[dv], dis[dv]).statistic)
            meds.append(float(np.median(b)))
        label = "全部" if n is None else f"{n:,}"
        print(f"{label:>12}{np.mean(rs):>13.4f}{np.std(rs):>12.4f}"
              f"{np.mean(rds):>10.4f}{np.mean(meds):>12.4f}")
        n_eff = n if n is not None else int(np.mean([  # 実効母集団サイズ
            (( yr > 0) & (yr < y)).sum() for y in by_year]))
        curve.append((n_eff, float(np.mean(rs))))

    # log(N) に対する線形トレンドで OpenAlex 全体（1.2 億本）へ外挿する
    xs = np.log10([c[0] for c in curve])
    ys = np.array([c[1] for c in curve])
    A = np.column_stack([np.ones(len(xs)), xs])
    coef, *_ = np.linalg.lstsq(A, ys, rcond=None)
    pred_1e8 = coef[0] + coef[1] * np.log10(1.2e8)
    r2 = 1 - np.sum((ys - A @ coef) ** 2) / np.sum((ys - ys.mean()) ** 2)

    print(f"\n=== log(母集団) への線形外挿 ===")
    print(f"  傾き {coef[1]:+.4f} / 桁あたり（決定係数 {r2:.3f}）")
    print(f"  N = 1.2 億本（OpenAlex 全体）での B の予測力: {pred_1e8:.4f}")
    print(f"\n  比較対象（今日の実測、サイズ残差化後）")
    print(f"    テキストのみ 768 次元       : 0.1892")
    print(f"    B_strict + 参考文献集合     : 0.2768")
    if pred_1e8 >= 0.1892:
        print(f"\n  ⚠️ 外挿値がテキストのみ（0.189）を上回る。第4章の優位が崩れる可能性。")
    else:
        print(f"\n  外挿値はテキストのみ（0.189）を下回る。優位は保たれる見込み。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
