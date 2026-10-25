"""コーパス内のコサイン類似度の分布を測る。

狙い: 最近傍距離（条件B）が情報を持つかを確かめる。
HindSight は「SPECTER2 の類似度が狭い範囲に集中する」と報告している（README）。
本当なら最近傍距離はほとんど弁別力を持たず、散らばり系の特徴量が必要になる。

使い方:
    uv run python src/analyze_similarity.py data/engine/corpus_emb
"""

import argparse
import json
import sys

import numpy as np


def quantiles(x: np.ndarray, label: str) -> None:
    qs = [0, 1, 5, 25, 50, 75, 95, 99, 100]
    v = np.percentile(x, qs)
    print(f"{label:<28}" + "".join(f"{val:>8.4f}" for val in v)
          + f"   (平均 {x.mean():.4f} / 標準偏差 {x.std():.4f})")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("prefix")
    ap.add_argument("--k", type=int, default=50, help="近傍の本数")
    ap.add_argument("--block", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    vecs = np.load(args.prefix + ".npy")
    meta = json.load(open(args.prefix + "_ids.json", encoding="utf-8"))
    n = len(vecs)
    print(f"コーパス {n} 本 / {vecs.shape[1]} 次元 / 正規化済み: {meta['normalized']}\n")

    # コサイン類似度にするため L2 正規化する（保存時は未正規化）
    unit = vecs / np.linalg.norm(vecs, axis=1, keepdims=True)

    rng = np.random.default_rng(args.seed)
    # ランダムなペアの類似度（同じ論文同士は除く）
    a = rng.integers(0, n, 1_000_000)
    b = rng.integers(0, n, 1_000_000)
    keep = a != b
    rand_sim = np.einsum("ij,ij->i", unit[a[keep]], unit[b[keep]])

    # 各論文の近傍 k 本の類似度。自分自身は除く
    nn1 = np.empty(n, dtype=np.float32)
    nnk = np.empty((n, args.k), dtype=np.float32)
    for s in range(0, n, args.block):
        e = min(s + args.block, n)
        sim = unit[s:e] @ unit.T                     # (block, n)
        rows = np.arange(e - s)
        sim[rows, np.arange(s, e)] = -np.inf         # 自分自身を外す
        part = np.partition(sim, -args.k, axis=1)[:, -args.k:]
        part.sort(axis=1)
        nnk[s:e] = part[:, ::-1]                     # 類似度の高い順
        nn1[s:e] = part[:, -1]

    print(f"{'':<28}{'min':>8}{'p1':>8}{'p5':>8}{'p25':>8}{'p50':>8}{'p75':>8}{'p95':>8}{'p99':>8}{'max':>8}")
    quantiles(rand_sim, "ランダムなペア")
    quantiles(nn1, "最近傍（1-NN）")
    quantiles(nnk[:, args.k - 1], f"第{args.k}近傍")
    print()

    # 最近傍距離（条件B に相当）がどれだけばらつくか
    b_score = 1.0 - nn1
    quantiles(b_score, "B = 1 - 最近傍類似度")

    # 近傍 k 本の散らばり（本研究の代理指標の素）
    spread = nnk[:, 0] - nnk[:, args.k - 1]
    quantiles(spread, f"近傍の幅（1-NN − {args.k}-NN）")

    print(f"\n--- 判定 ---")
    iqr_rand = np.percentile(rand_sim, 75) - np.percentile(rand_sim, 25)
    iqr_b = np.percentile(b_score, 75) - np.percentile(b_score, 25)
    print(f"ランダムペア類似度の四分位範囲: {iqr_rand:.4f}")
    print(f"B（最近傍距離）の四分位範囲    : {iqr_b:.4f}")
    overlap = (rand_sim > np.percentile(nn1, 5)).mean()
    print(f"ランダムペアが「最近傍の下位5%」より似ている割合: {100*overlap:.2f}%")
    print(f"  → この割合が大きいほど、最近傍距離は『近いか遠いか』を弁別できていない")

    np.save(args.prefix + "_nn1.npy", nn1)
    np.save(args.prefix + f"_nn{args.k}.npy", nnk)
    print(f"\n保存: {args.prefix}_nn1.npy / {args.prefix}_nn{args.k}.npy")
    return 0


if __name__ == "__main__":
    sys.exit(main())
