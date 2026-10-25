"""検証①: 「動き」が既存指標（D-index・atypicality・最近傍距離 B）と別物かを確かめる。

B（最近傍距離）は「動き」と同じ SciSciNet の埋め込みで計算し直す（整合性のため）。
母集団は対象論文 22,302 本（ML 2016-2018）。
"""

import csv
import json
import sys

import numpy as np
from scipy.stats import spearmanr

EMB = "data/engine/sciscinet_emb"
MOVE = "data/engine/movement.csv"
TARGETS = "data/engine/corpus_ids.csv"
OUT = "data/engine/validation.csv"


def main() -> int:
    vecs = np.load(EMB + ".npy")
    ids = json.load(open(EMB + "_ids.json", encoding="utf-8"))["paperids"]
    pos = {p: i for i, p in enumerate(ids)}

    tgt_ids = [r["paperid"] for r in csv.DictReader(open(TARGETS, encoding="utf-8"))]
    have = [p for p in tgt_ids if p in pos]
    idx = np.array([pos[p] for p in have])
    U = vecs[idx] / np.linalg.norm(vecs[idx], axis=1, keepdims=True)
    print(f"対象コーパス {len(have)} 本で最近傍距離 B を計算", flush=True)

    nn1 = np.empty(len(U), dtype=np.float32)
    for s in range(0, len(U), 2000):
        e = min(s + 2000, len(U))
        sim = U[s:e] @ U.T
        sim[np.arange(e - s), np.arange(s, e)] = -np.inf
        nn1[s:e] = sim.max(axis=1)
    b_by_id = {p: 1.0 - float(v) for p, v in zip(have, nn1)}
    dup = {p for p, v in zip(have, nn1) if v > 0.9999}
    print(f"ほぼ同一テキストの重複 {len(dup)} 本を除外する", flush=True)

    rows = [r for r in csv.DictReader(open(MOVE, encoding="utf-8"))
            if r["paperid"] not in dup and r["paperid"] in b_by_id]
    print(f"評価対象 {len(rows)} 本\n", flush=True)

    def col(k, f=float):
        return np.array([f(r[k]) if r[k] else np.nan for r in rows])

    feats = {
        "動き (1-cos(過去,未来))": col("movement"),
        "B (最近傍距離)":          np.array([b_by_id[r["paperid"]] for r in rows]),
        "過去の分離度":            col("past_separation"),
        "未来の分離度":            col("future_separation"),
        "融合 (過去-未来の分離度)": col("fusion"),
        "過去の重心散らばり":      col("past_centroid_spread"),
    }
    targets = {
        "disruption":    (col("disruption"), np.array([r["d_valid"] == "true" for r in rows])),
        "Atyp_Median_Z": (col("Atyp_Median_Z"), ~np.isnan(col("Atyp_Median_Z"))),
        "log(1+引用)":   (np.log1p(col("citation_count", int)), np.ones(len(rows), bool)),
    }

    print("=== 事前/事後の特徴量どうしの相関（Spearman）===")
    names = list(feats)
    print(f"{'':<24}" + "".join(f"{n[:10]:>12}" for n in names))
    for a in names:
        row = f"{a:<24}"
        for b in names:
            r = 1.0 if a == b else spearmanr(feats[a], feats[b], nan_policy="omit").statistic
            row += f"{r:>12.3f}"
        print(row)

    print("\n=== 既存の事後指標との相関（Spearman）===")
    print(f"{'':<24}" + "".join(f"{t:>22}" for t in targets))
    for fname, fv in feats.items():
        row = f"{fname:<24}"
        for tname, (tv, mask) in targets.items():
            m = mask & ~np.isnan(fv) & ~np.isnan(tv)
            r = spearmanr(fv[m], tv[m]).statistic
            row += f"{r:>14.4f} (n={m.sum():>5})"
        print(row)

    # 後の可視化・予測で使うため結合結果を保存
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["paperid", "year", "doctype", "n_past", "n_future", "movement", "B",
                    "past_separation", "future_separation", "fusion",
                    "past_centroid_spread", "future_centroid_spread",
                    "disruption", "d_valid", "Atyp_Median_Z", "citation_count"])
        for r in rows:
            w.writerow([r["paperid"], r["year"], r["doctype"], r["n_past"], r["n_future"],
                        r["movement"], b_by_id[r["paperid"]],
                        r["past_separation"], r["future_separation"], r["fusion"],
                        r["past_centroid_spread"], r["future_centroid_spread"],
                        r["disruption"], r["d_valid"], r["Atyp_Median_Z"], r["citation_count"]])
    print(f"\n保存: {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
