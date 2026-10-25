"""「動き」を2点間の距離から軌跡に拡張する。

これまでの「動き」は、参考文献の重心 p と 5年窓の被引用の重心 f の2点間距離だった。
どう動いたか（経路の形）は見ていない。

ここでは未来集合を year_diff で累積的に切り、重心の列を作る:

    p ──→ f1 ──→ f2 ──→ f3 ──→ f4 ──→ f5
         (≤1年) (≤2年) (≤3年) (≤4年) (≤5年)

累積にする理由: 各年だけの被引用は中央値 3〜5 本で重心が不安定。
累積なら最低 5 本以上ある論文が 8,841 本（ほぼ全部）残る。

測る特徴量（狙い: 既存の「動き」は参考文献数に強く依存するが、
比や角度で定義した量はサイズの影響を受けにくいはず）:

  dist_d      : 1 − cos(p, f_d)。これが単調増加するか＝「徐々に離れていく」の検証
  path_len    : Σ (1 − cos(f_d, f_{d+1}))。経路の長さ
  detour      : path_len ÷ dist_5。迂回度。1 に近い＝直進、大きい＝迂回
  monotonic   : dist_d が単調増加した区間の割合
  consistency : 各ステップの移動方向の cos 類似度の平均。方向の一貫性
"""

import csv
import json
import sys
from collections import defaultdict

import numpy as np
from scipy.stats import spearmanr

EMB = "data/engine/sciscinet_emb"
EDGES = "data/engine/edges.csv"
VAL = "data/engine/validation_strict.csv"
OUT = "data/engine/trajectory.csv"
MIN_CUM = 5          # 累積でこの本数以上ないと軌跡を作らない
MAX_D = 5


def main() -> int:
    vecs = np.load(EMB + ".npy")
    ids = json.load(open(EMB + "_ids.json", encoding="utf-8"))["paperids"]
    pos = {p: i for i, p in enumerate(ids)}
    unit = vecs / np.linalg.norm(vecs, axis=1, keepdims=True)

    base = {r["paperid"]: r for r in csv.DictReader(open(VAL, encoding="utf-8"))}
    print(f"評価対象 {len(base)} 本", flush=True)

    # 過去集合と、year_diff 別の未来集合を集める
    past: dict[str, list[int]] = defaultdict(list)
    fut: dict[str, dict[int, list[int]]] = defaultdict(lambda: defaultdict(list))
    with open(EDGES, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["is_past_edge"] == "true" and int(r["year_diff"]) >= 0:
                i = pos.get(r["cited_paperid"])
                if i is not None and r["citing_paperid"] in base:
                    past[r["citing_paperid"]].append(i)
            if r["is_future_edge"] == "true":
                d = int(r["year_diff"])
                i = pos.get(r["citing_paperid"])
                if i is not None and r["cited_paperid"] in base and 0 <= d <= MAX_D:
                    fut[r["cited_paperid"]][d].append(i)

    def centroid(idx: list[int]) -> np.ndarray:
        c = unit[idx].mean(axis=0)
        return c / np.linalg.norm(c)

    rows = []
    for pid, meta in base.items():
        pi = past.get(pid, [])
        if len(pi) < 5:
            continue
        # 累積の未来集合
        cum: list[int] = []
        cents, sizes = [], []
        ok = True
        for d in range(0, MAX_D + 1):
            cum.extend(fut[pid].get(d, []))
            if d == 0:
                continue                      # 同年は中央値 0 本なので起点にしない
            if len(cum) < MIN_CUM:
                ok = False
                break
            cents.append(centroid(cum))
            sizes.append(len(cum))
        if not ok or len(cents) < MAX_D:
            continue

        p = centroid(pi)
        F = np.stack(cents)                   # (5, 768)

        dist = 1.0 - F @ p                    # dist_1..dist_5
        # 経路長: 連続する重心の間の距離
        steps = np.array([1.0 - float(F[d] @ F[d + 1]) for d in range(MAX_D - 1)])
        path_len = float(steps.sum())
        detour = path_len / float(dist[-1]) if dist[-1] > 1e-9 else np.nan
        monotonic = float(np.mean(np.diff(dist) > 0))
        # 方向の一貫性: 各ステップの変位ベクトルの cos の平均
        disp = np.diff(np.vstack([p, F]), axis=0)          # (5, 768)
        nrm = np.linalg.norm(disp, axis=1, keepdims=True)
        nrm[nrm < 1e-12] = 1.0
        dn = disp / nrm
        cons = float(np.mean([dn[i] @ dn[i + 1] for i in range(len(dn) - 1)]))

        rows.append({
            "paperid": pid,
            "year": meta["year"],
            "n_past": meta["n_past"],
            "n_future": meta["n_future"],
            **{f"dist_{d+1}": f"{dist[d]:.6f}" for d in range(MAX_D)},
            "path_len": f"{path_len:.6f}",
            "detour": f"{detour:.6f}" if detour == detour else "",
            "monotonic": f"{monotonic:.4f}",
            "consistency": f"{cons:.6f}",
            "movement": meta["movement"],
            "B_strict": meta["B_strict"],
            "past_separation": meta["past_separation"],
            "disruption": meta["disruption"],
            "d_valid": meta["d_valid"],
            "Atyp_Median_Z": meta["Atyp_Median_Z"],
            "citation_count": meta["citation_count"],
        })

    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)
    print(f"軌跡を作れた論文: {len(rows)} 本\n")

    def col(k, f=float):
        return np.array([f(r[k]) if r[k] else np.nan for r in rows])

    # --- 1. 徐々に離れていくか ---
    D = np.vstack([col(f"dist_{d}") for d in range(1, MAX_D + 1)])
    print("=== 1. 出発点からの距離は単調に増えるか ===")
    print(f"  {'':<10}{'p25':>9}{'p50':>9}{'p75':>9}{'平均':>9}")
    for d in range(MAX_D):
        q = np.percentile(D[d], [25, 50, 75])
        print(f"  dist_{d+1:<5}{q[0]:>9.4f}{q[1]:>9.4f}{q[2]:>9.4f}{D[d].mean():>9.4f}")
    mono = col("monotonic")
    print(f"\n  全区間で単調増加した論文: {(mono == 1.0).mean()*100:.1f}%")
    print(f"  単調増加した区間の割合（平均）: {mono.mean():.3f}")
    print(f"  dist_5 > dist_1 の論文: {(D[4] > D[0]).mean()*100:.1f}%")

    # --- 2. 新しい特徴量の分布 ---
    print("\n=== 2. 軌跡の特徴量 ===")
    print(f"  {'':<16}{'p5':>9}{'p50':>9}{'p95':>9}{'平均':>9}")
    feats = {"経路長": col("path_len"), "迂回度": col("detour"),
             "方向の一貫性": col("consistency"), "単調性": mono}
    for nm, v in feats.items():
        q = np.percentile(v[~np.isnan(v)], [5, 50, 95])
        print(f"  {nm:<16}{q[0]:>9.4f}{q[1]:>9.4f}{q[2]:>9.4f}{np.nanmean(v):>9.4f}")

    # --- 3. サイズ依存性（本命） ---
    npast, nfut = col("n_past", int), col("n_future", int)
    print("\n=== 3. サイズ依存性（今の『動き』の弱点を解決するか）===")
    print(f"  {'':<16}{'× n_past':>11}{'× n_future':>12}")
    allf = {"動き（2点間）": col("movement"), **feats}
    for nm, v in allf.items():
        m = ~np.isnan(v)
        print(f"  {nm:<16}{spearmanr(v[m], npast[m]).statistic:>11.3f}"
              f"{spearmanr(v[m], nfut[m]).statistic:>12.3f}")

    # --- 4. 既存指標との相関 ---
    dis, atyp = col("disruption"), col("Atyp_Median_Z")
    dv = np.array([r["d_valid"] == "true" for r in rows])
    cit = col("citation_count", int)
    print("\n=== 4. 既存指標との相関 ===")
    print(f"  {'':<16}{'× disruption':>15}{'× Atyp':>11}{'× log(1+引用)':>15}{'× 動き':>10}")
    mv = col("movement")
    for nm, v in allf.items():
        m1 = dv & ~np.isnan(v); m2 = ~np.isnan(atyp) & ~np.isnan(v); m3 = ~np.isnan(v)
        print(f"  {nm:<16}{spearmanr(v[m1], dis[m1]).statistic:>15.4f}"
              f"{spearmanr(v[m2], atyp[m2]).statistic:>11.4f}"
              f"{spearmanr(v[m3], np.log1p(cit[m3])).statistic:>15.4f}"
              f"{spearmanr(v[m3], mv[m3]).statistic:>10.4f}")
    print(f"\n保存: {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
