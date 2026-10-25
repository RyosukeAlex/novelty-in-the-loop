"""B（最近傍距離）を出版年以前のコーパスに限って再計算し、検証①②を取り直す。

なぜ必要か:
  これまでの B は「ML 2016-2018 の対象論文 22,281 本」の中での最近傍だった。
  2016 年の論文の最近傍が 2018 年の論文になりうる＝出版時点に存在しないものを見ていた。
  これは条件B（AI Scientist の最近傍チェック相当）を有利にするリークである。

B_strict の定義:
  対象論文 i（出版年 y_i）について、母集団は「埋め込みがあり year < y_i の論文」。
  同年は除外する（厳密には月単位で切るべきだが、保守的に年で切る）。

母集団の限界（結果に書く）:
  この母集団は「対象が引用した論文＋対象を引用した論文」の集合なので、
  ML 分野に偏った部分集合であり、全既存研究ではない。
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
OUT = "data/engine/validation_strict.csv"


def main() -> int:
    vecs = np.load(EMB + ".npy")
    ids = json.load(open(EMB + "_ids.json", encoding="utf-8"))["paperids"]
    pos = {p: i for i, p in enumerate(ids)}
    unit = vecs / np.linalg.norm(vecs, axis=1, keepdims=True)

    year_of = {}
    for r in csv.DictReader(open(YEARS, encoding="utf-8")):
        if r["year"] and r["paperid"] in pos:
            year_of[r["paperid"]] = int(r["year"])
    yr = np.full(len(ids), -1, dtype=np.int32)
    for p, y in year_of.items():
        yr[pos[p]] = y

    rows = [r for r in csv.DictReader(open(VAL, encoding="utf-8")) if r["paperid"] in pos]
    print(f"評価対象 {len(rows)} 本", flush=True)

    # 年ごとに母集団を切り替えて最近傍を取る
    b_strict = np.full(len(rows), np.nan, dtype=np.float32)
    by_year: dict[int, list[int]] = {}
    for k, r in enumerate(rows):
        by_year.setdefault(int(r["year"]), []).append(k)

    for y, ks in sorted(by_year.items()):
        pool = np.where((yr > 0) & (yr < y))[0]
        P = unit[pool]
        tgt = np.array([pos[rows[k]["paperid"]] for k in ks])
        print(f"  {y} 年: 対象 {len(ks):,} 本 / 母集団 {len(pool):,} 本", flush=True)
        for s in range(0, len(tgt), 500):
            e = min(s + 500, len(tgt))
            sim = unit[tgt[s:e]] @ P.T
            best = sim.max(axis=1)
            for j, k in enumerate(ks[s:e]):
                b_strict[k] = 1.0 - float(best[j])

    def col(k, f=float):
        return np.array([f(r[k]) if r[k] else np.nan for r in rows])

    mv = col("movement"); b_old = col("B")
    psep, pcent = col("past_separation"), col("past_centroid_spread")
    n_past, n_future = col("n_past", int), col("n_future", int)
    dis, atyp, cit = col("disruption"), col("Atyp_Median_Z"), col("citation_count", int)
    dv = np.array([r["d_valid"] == "true" for r in rows])

    print(f"\n=== B の分布の比較 ===")
    print(f"  {'':<22}{'p5':>9}{'p50':>9}{'p95':>9}{'平均':>9}")
    for nm, v in (("B（旧・リークあり）", b_old), ("B_strict（出版年以前）", b_strict)):
        q = np.percentile(v, [5, 50, 95])
        print(f"  {nm:<22}{q[0]:>9.4f}{q[1]:>9.4f}{q[2]:>9.4f}{v.mean():>9.4f}")
    print(f"  両者の順位相関: {spearmanr(b_old, b_strict).statistic:.4f}")

    print(f"\n=== 検証①: 既存指標との相関 ===")
    print(f"  {'':<22}{'× disruption':>16}{'× Atyp':>12}{'× log(1+引用)':>16}{'× 動き':>10}")
    for nm, v in (("動き", mv), ("B（旧）", b_old), ("B_strict", b_strict), ("過去の分離度", psep)):
        m1 = dv & ~np.isnan(v)
        m2 = ~np.isnan(atyp) & ~np.isnan(v)
        r1 = spearmanr(v[m1], dis[m1]).statistic
        r2 = spearmanr(v[m2], atyp[m2]).statistic
        r3 = spearmanr(v, np.log1p(cit), nan_policy="omit").statistic
        r4 = spearmanr(v, mv, nan_policy="omit").statistic
        print(f"  {nm:<22}{r1:>16.4f}{r2:>12.4f}{r3:>16.4f}{r4:>10.4f}")

    print(f"\n=== 検証①: 層別の『× disruption』 ===")
    print(f"  {'層':<10}{'本数':>7}{'動き':>10}{'B（旧）':>11}{'B_strict':>11}")
    for lo, hi, lab in [(5,9,"5–9"),(10,19,"10–19"),(20,49,"20–49"),(50,99,"50–99"),(100,10**9,"100+")]:
        m = (n_future >= lo) & (n_future <= hi) & dv
        if m.sum() < 100: continue
        print(f"  {lab:<10}{m.sum():>7}"
              f"{spearmanr(mv[m], dis[m]).statistic:>10.3f}"
              f"{spearmanr(b_old[m], dis[m]).statistic:>11.3f}"
              f"{spearmanr(b_strict[m], dis[m]).statistic:>11.3f}")

    # 検証②: B を差し替えて予測を取り直す
    X_text = unit[np.array([pos[r["paperid"]] for r in rows])]
    Z = np.column_stack([np.ones(len(rows)), np.log(n_past), np.log(n_future)])
    y_res = mv - Z @ np.linalg.lstsq(Z, mv, rcond=None)[0]

    models = {
        "M1 B（旧・リークあり）":        np.column_stack([b_old]),
        "M1s B_strict のみ":            np.column_stack([b_strict]),
        "M3 テキスト 768 次元":          X_text,
        "M2s B_strict + 参考文献集合":   np.column_stack([b_strict, psep, pcent, np.log(n_past)]),
    }
    kf = KFold(n_splits=5, shuffle=True, random_state=42)
    print(f"\n=== 検証②: サイズ残差化した動きの予測 ===")
    print(f"  {'モデル':<30}{'Spearman':>11}{'対 B_strict':>13}")
    base = None
    res = {}
    for mname, X in models.items():
        pipe = make_pipeline(StandardScaler(), Ridge(alpha=10.0))
        pred = cross_val_predict(pipe, X, y_res, cv=kf, n_jobs=-1)
        r = spearmanr(pred, y_res).statistic
        res[mname] = r
        if "M1s" in mname:
            base = r
    for mname, r in res.items():
        ratio = f"{r/base:>12.2f} 倍" if base and base > 0 else "—"
        print(f"  {mname:<30}{r:>11.4f}{ratio:>13}")

    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(list(rows[0]) + ["B_strict"])
        for k, r in enumerate(rows):
            w.writerow(list(r.values()) + [f"{b_strict[k]:.6f}"])
    print(f"\n保存: {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
