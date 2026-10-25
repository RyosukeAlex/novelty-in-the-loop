"""年を跨いだ分割で汎化を確認する（第3章の前提）。

2016–2017 年の論文で学習し、2018 年の論文を予測する。
時点分割の設計は Impact4Cast（Gu & Krenn 2025）に倣う:
  学習に使う期間の情報だけで特徴量と前処理を決め、評価期間のデータは一切使わない。

前回より厳しくした点:
  サイズ残差化（log(n_past)・log(n_future) の線形成分の除去）を、
  **学習データだけで係数を推定し、評価データに適用する**。
  前回は全データで残差化していたため、残差化の係数に評価データの情報が入っていた。
  比較のため、ランダム CV 側も同じ手順で計算し直す。

予想（実行前に立てた）:
  2018 年の論文は 5 年窓が 2023 年までで、OpenAlex の登録遅れにより未来集合が過小になる
  （docs/handover.md §3-5）。したがって分布シフトが生じ、性能は落ちるはず。
"""

import csv
import json
import sys

import numpy as np
from scipy.stats import spearmanr
from sklearn.linear_model import Ridge
from sklearn.model_selection import KFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

EMB = "data/engine/sciscinet_emb"
VAL = "data/engine/validation_strict.csv"


def residualize(y, Z, fit_mask):
    """Z の線形成分を y から除く。係数は fit_mask の行だけで推定する。"""
    coef, *_ = np.linalg.lstsq(Z[fit_mask], y[fit_mask], rcond=None)
    return y - Z @ coef


def main() -> int:
    vecs = np.load(EMB + ".npy")
    ids = json.load(open(EMB + "_ids.json", encoding="utf-8"))["paperids"]
    pos = {p: i for i, p in enumerate(ids)}
    unit = vecs / np.linalg.norm(vecs, axis=1, keepdims=True)

    rows = [r for r in csv.DictReader(open(VAL, encoding="utf-8")) if r["paperid"] in pos]
    def col(k, f=float):
        return np.array([f(r[k]) if r[k] else np.nan for r in rows])

    year = col("year", int)
    mv = col("movement")
    b = col("B_strict")
    psep, pcent = col("past_separation"), col("past_centroid_spread")
    n_past, n_future = col("n_past", int), col("n_future", int)
    X_text = unit[np.array([pos[r["paperid"]] for r in rows])]
    Z = np.column_stack([np.ones(len(rows)), np.log(n_past), np.log(n_future)])

    print(f"全体 {len(rows)} 本", flush=True)
    print(f"\n=== 年ごとの分布（分布シフトの確認）===")
    print(f"  {'年':<6}{'本数':>7}{'n_future p50':>14}{'n_future 平均':>15}"
          f"{'動き p50':>12}{'B p50':>10}")
    for y in (2016, 2017, 2018):
        m = year == y
        print(f"  {y:<6}{m.sum():>7}{np.median(n_future[m]):>14.0f}"
              f"{n_future[m].mean():>15.1f}{np.median(mv[m]):>12.4f}{np.median(b[m]):>10.4f}")

    models = {
        "B_strict のみ":            np.column_stack([b]),
        "テキスト 768 次元":         X_text,
        "B + 参考文献集合":          np.column_stack([b, psep, pcent, np.log(n_past)]),
        "B + 参考文献集合 + テキスト": np.column_stack([b, psep, pcent, np.log(n_past), X_text]),
    }

    tr = (year <= 2017)
    te = (year == 2018)
    print(f"\n学習 2016–2017: {tr.sum()} 本 / 評価 2018: {te.sum()} 本")

    # 残差化の係数は学習データだけで推定する
    y_res_tr = residualize(mv, Z, tr)
    # ランダム CV 用: fold ごとに学習側で残差化する
    kf = KFold(n_splits=5, shuffle=True, random_state=42)

    print(f"\n{'モデル':<30}{'ランダムCV':>12}{'年を跨いだ分割':>16}{'差':>9}")
    for mname, X in models.items():
        # --- ランダム CV（fold 内で残差化） ---
        preds = np.full(len(rows), np.nan)
        ys = np.full(len(rows), np.nan)
        for itr, ite in kf.split(X):
            mask = np.zeros(len(rows), bool); mask[itr] = True
            yr_ = residualize(mv, Z, mask)
            pipe = make_pipeline(StandardScaler(), Ridge(alpha=10.0))
            pipe.fit(X[itr], yr_[itr])
            preds[ite] = pipe.predict(X[ite])
            ys[ite] = yr_[ite]
        r_cv = spearmanr(preds, ys).statistic

        # --- 年を跨いだ分割 ---
        pipe = make_pipeline(StandardScaler(), Ridge(alpha=10.0))
        pipe.fit(X[tr], y_res_tr[tr])
        pred_te = pipe.predict(X[te])
        r_tmp = spearmanr(pred_te, y_res_tr[te]).statistic

        print(f"  {mname:<30}{r_cv:>12.4f}{r_tmp:>16.4f}{r_tmp - r_cv:>+9.4f}")

    # 逆方向も見る（分布シフトの方向性を確認するため）
    tr2, te2 = (year == 2018), (year <= 2017)
    y_res_tr2 = residualize(mv, Z, tr2)
    print(f"\n=== 参考: 逆方向（2018 学習 → 2016–2017 評価）===")
    print(f"  {'モデル':<30}{'Spearman':>11}")
    for mname, X in models.items():
        pipe = make_pipeline(StandardScaler(), Ridge(alpha=10.0))
        pipe.fit(X[tr2], y_res_tr2[tr2])
        r = spearmanr(pipe.predict(X[te2]), y_res_tr2[te2]).statistic
        print(f"  {mname:<30}{r:>11.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
