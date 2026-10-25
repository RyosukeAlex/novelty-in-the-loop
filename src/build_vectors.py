"""過去ベクトル・未来ベクトルを作り、「動き」としての新規性を算出する。

過去ベクトル = 参考文献の埋め込みの重心（year_diff >= 0 のエッジのみ。リーク対策）
未来ベクトル = 被引用論文の埋め込みの重心（5 年窓）
動き         = 1 - cos(過去ベクトル, 未来ベクトル)

重心は L2 正規化してから平均する（方向の重心）。SPECTER2 のノルムは 22.08±0.16 で
ほぼ一定なので実質差はないが、「方向の平均」の方が意味が明確。

散らばり系（docs/engine-v0.md §4 で B と独立だと確認した分離度を中心に）も
過去集合・未来集合それぞれについて算出する。

使い方:
    uv run python src/build_vectors.py
"""

import csv
import json
import pathlib
import sys

import numpy as np

EMB = "data/engine/sciscinet_emb"
EDGES = "data/engine/edges.csv"
TARGETS = "data/engine/corpus_ids.csv"
OUT = "data/engine/movement.csv"
MIN_SET = 5          # 過去・未来それぞれこの本数以上で算出する


def spread_stats(nb: np.ndarray) -> tuple[float, float, float, float]:
    """集合の散らばり: (重心からの平均距離, 最大ペア間距離, 平均ペア間距離, 分離度)"""
    c = nb.mean(axis=0)
    c /= np.linalg.norm(c)
    cent = float((1.0 - nb @ c).mean())
    pd = 1.0 - nb @ nb.T
    iu = np.triu_indices(len(nb), 1)
    pv = pd[iu]
    pmax, pmean = float(pv.max()), float(pv.mean())
    return cent, pmax, pmean, (pmax / pmean if pmean > 0 else np.nan)


def main() -> int:
    vecs = np.load(EMB + ".npy")
    ids = json.load(open(EMB + "_ids.json", encoding="utf-8"))["paperids"]
    pos = {p: i for i, p in enumerate(ids)}
    unit = vecs / np.linalg.norm(vecs, axis=1, keepdims=True)
    print(f"埋め込み {len(ids)} 件", flush=True)

    # 対象論文（ML 2016-2018）と既存指標
    targets = {}
    with open(TARGETS, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            targets[r["paperid"]] = r
    print(f"対象 {len(targets)} 件", flush=True)

    # エッジから過去集合・未来集合を作る
    past: dict[str, list[int]] = {}
    future: dict[str, list[int]] = {}
    n_skip_emb = 0
    with open(EDGES, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["is_past_edge"] == "true" and int(r["year_diff"]) >= 0:
                i = pos.get(r["cited_paperid"])
                if i is None:
                    n_skip_emb += 1
                else:
                    past.setdefault(r["citing_paperid"], []).append(i)
            if r["is_future_edge"] == "true":
                i = pos.get(r["citing_paperid"])
                if i is None:
                    n_skip_emb += 1
                else:
                    future.setdefault(r["cited_paperid"], []).append(i)
    print(f"過去集合を持つ論文 {len(past)} 件 / 未来集合 {len(future)} 件 "
          f"/ 埋め込み欠損で捨てたエッジ {n_skip_emb} 本", flush=True)

    rows = []
    for pid, meta in targets.items():
        pi = past.get(pid, [])
        fi = future.get(pid, [])
        if len(pi) < MIN_SET or len(fi) < MIN_SET:
            continue
        P = unit[pi]
        F = unit[fi]
        pc = P.mean(axis=0); pc /= np.linalg.norm(pc)
        fc = F.mean(axis=0); fc /= np.linalg.norm(fc)

        movement = 1.0 - float(pc @ fc)
        p_cent, p_max, p_mean, p_sep = spread_stats(P)
        f_cent, f_max, f_mean, f_sep = spread_stats(F)

        rows.append({
            "paperid": pid,
            "year": meta["year"],
            "doctype": meta["doctype"],
            "n_past": len(pi),
            "n_future": len(fi),
            "movement": movement,
            "past_centroid_spread": p_cent,
            "past_max_pair": p_max,
            "past_separation": p_sep,
            "future_centroid_spread": f_cent,
            "future_max_pair": f_max,
            "future_separation": f_sep,
            # 融合 signature の代理: 過去が散らばり未来がまとまるなら正に大きい
            "fusion": p_sep - f_sep,
            "disruption": meta["disruption"],
            "d_valid": meta["d_valid"],
            "Atyp_Median_Z": meta["Atyp_Median_Z"],
            "citation_count": meta["citation_count"],
            "reference_count": meta["reference_count"],
        })

    pathlib.Path(OUT).parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    mv = np.array([r["movement"] for r in rows])
    print(f"\n算出できた論文: {len(rows)} 件（過去・未来ともに {MIN_SET} 本以上）")
    print(f"動きの分布: p5 {np.percentile(mv,5):.4f} / p50 {np.percentile(mv,50):.4f} "
          f"/ p95 {np.percentile(mv,95):.4f} / 平均 {mv.mean():.4f}")
    print(f"保存: {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
