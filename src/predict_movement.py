"""検証②: 出版時点のテキストから「動き」を予測できるか（成否条件②）。

README の問い:「テキストから、非類似度（B）を超えて『動き』を予測できるか」

設計上の注意:
  1. 目的変数（動き）は未来集合の大きさ n_future（= 5年窓の被引用数）と -0.56 で相関する。
     素朴に予測すると「被引用数を当てているだけ」になるため、
     **サイズを残差化した動き**も目的変数に入れて両方で評価する。
  2. 特徴量に n_future を入れてはいけない（出版時点で未知）。
     使えるのは対象論文のテキスト埋め込み、参考文献から作れる量、B。
  3. B は「コーパス全体での最近傍」なので、対象論文より後の論文を含む（リーク）。
     厳密には出版年以前に限るべき。今日は簡易版。
"""

import csv
import json
import sys

import numpy as np
from scipy.stats import spearmanr
from sklearn.linear_model import Ridge
from sklearn.model_selection import KFold, cross_val_predict
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline

EMB = "data/engine/sciscinet_emb"
VAL = "data/engine/validation.csv"
SEED = 42


def main() -> int:
    vecs = np.load(EMB + ".npy")
    ids = json.load(open(EMB + "_ids.json", encoding="utf-8"))["paperids"]
    pos = {p: i for i, p in enumerate(ids)}

    rows = [r for r in csv.DictReader(open(VAL, encoding="utf-8")) if r["paperid"] in pos]
    print(f"評価対象 {len(rows)} 本", flush=True)

    def col(k, f=float):
        return np.array([f(r[k]) if r[k] else np.nan for r in rows])

    # 対象論文自身の埋め込み（= 出版時点のテキスト）
    X_text = vecs[np.array([pos[r["paperid"]] for r in rows])]
    X_text = X_text / np.linalg.norm(X_text, axis=1, keepdims=True)

    y_raw = col("movement")
    B = col("B")
    psep, pcent = col("past_separation"), col("past_centroid_spread")
    n_past, n_future = col("n_past", int), col("n_future", int)

    # サイズを残差化した動き（log サイズの線形成分を除去）
    Z = np.column_stack([np.ones(len(rows)), np.log(n_past), np.log(n_future)])
    y_res = y_raw - Z @ np.linalg.lstsq(Z, y_raw, rcond=None)[0]

    models = {
        "M0 参考文献数のみ（出版時点のサイズ）": np.column_stack([np.log(n_past)]),
        "M1 B のみ（= 条件B 相当）":            np.column_stack([B]),
        "M2 B + 参考文献集合の散らばり":         np.column_stack([B, psep, pcent, np.log(n_past)]),
        "M3 テキスト埋め込み 768 次元":          X_text,
        "M4 M2 + テキスト埋め込み":              np.column_stack([B, psep, pcent, np.log(n_past), X_text]),
    }

    kf = KFold(n_splits=5, shuffle=True, random_state=SEED)
    for yname, y in (("動き（生）", y_raw), ("動き（サイズ残差化）", y_res)):
        print(f"\n=== 目的変数: {yname} ===")
        print(f"  {'モデル':<34}{'Spearman':>11}{'R2':>9}")
        for mname, X in models.items():
            pipe = make_pipeline(StandardScaler(), Ridge(alpha=10.0))
            pred = cross_val_predict(pipe, X, y, cv=kf, n_jobs=-1)
            r = spearmanr(pred, y).statistic
            ss = 1 - np.sum((y - pred) ** 2) / np.sum((y - y.mean()) ** 2)
            print(f"  {mname:<34}{r:>11.4f}{ss:>9.4f}")

    # 層内での予測（サイズの影響を物理的に抑える）
    print("\n=== 未来集合サイズの層内で予測（目的変数: 動き（生））===")
    print(f"  {'層':<10}{'本数':>7}{'M1 B':>10}{'M3 テキスト':>13}{'M4 併用':>11}")
    for lo, hi, lab in [(5,9,"5–9"),(10,19,"10–19"),(20,49,"20–49"),(50,10**9,"50+")]:
        m = (n_future >= lo) & (n_future <= hi)
        if m.sum() < 300:
            continue
        kf2 = KFold(n_splits=5, shuffle=True, random_state=SEED)
        out = []
        for X in (models["M1 B のみ（= 条件B 相当）"], models["M3 テキスト埋め込み 768 次元"],
                  models["M4 M2 + テキスト埋め込み"]):
            pipe = make_pipeline(StandardScaler(), Ridge(alpha=10.0))
            pred = cross_val_predict(pipe, X[m], y_raw[m], cv=kf2, n_jobs=-1)
            out.append(spearmanr(pred, y_raw[m]).statistic)
        print(f"  {lab:<10}{m.sum():>7}{out[0]:>10.4f}{out[1]:>13.4f}{out[2]:>11.4f}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
