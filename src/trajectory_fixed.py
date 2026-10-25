"""軌跡を「各年から固定本数」で測り直す。

前の累積方式の誤り（src/trajectory.py）:
  累積重心と出発点の距離は、大数の法則で自動的に縮む。
  ランダム順に n 本選んでも 99.3% の論文で距離が減少したため、
  観測された減少は時間の効果ではなくサンプル数の効果だった。

正しい設計:
  各年（year_diff = 1..5）から **同じ本数 k 本** をランダムに取って重心を作る。
  全段で本数が揃うので、サンプル数の効果が消える。試行を繰り返して平均する。

対照実験:
  時間を無視して未来集合全体から k 本取る系列も作る。
  ランダム順では dist は d に依存しないはず（フラット）。
  時間順で増加や減少が出れば、それが時間に固有の効果である。
"""

import csv
import json
import sys
from collections import defaultdict

import numpy as np
from scipy.stats import spearmanr, wilcoxon

EMB = "data/engine/sciscinet_emb"
EDGES = "data/engine/edges.csv"
VAL = "data/engine/validation_strict.csv"
OUT = "data/engine/trajectory_fixed.csv"
K = 3          # 各年から取る本数
TRIALS = 10
MAX_D = 5
SEED = 5


def main() -> int:
    vecs = np.load(EMB + ".npy")
    ids = json.load(open(EMB + "_ids.json", encoding="utf-8"))["paperids"]
    pos = {p: i for i, p in enumerate(ids)}
    unit = vecs / np.linalg.norm(vecs, axis=1, keepdims=True)

    base = {r["paperid"]: r for r in csv.DictReader(open(VAL, encoding="utf-8"))}
    past = defaultdict(list)
    fut = defaultdict(lambda: defaultdict(list))
    with open(EDGES, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            d = int(r["year_diff"])
            if r["is_past_edge"] == "true" and d >= 0:
                i = pos.get(r["cited_paperid"])
                if i is not None and r["citing_paperid"] in base:
                    past[r["citing_paperid"]].append(i)
            if r["is_future_edge"] == "true" and 1 <= d <= MAX_D:
                i = pos.get(r["citing_paperid"])
                if i is not None and r["cited_paperid"] in base:
                    fut[r["cited_paperid"]][d].append(i)

    # 各年に K 本以上ある論文だけ
    pids = [p for p in base
            if len(past[p]) >= 5 and all(len(fut[p].get(d, [])) >= K for d in range(1, MAX_D + 1))]
    print(f"対象 {len(pids)} 本（各年に {K} 本以上 / 参考文献 5 本以上）", flush=True)

    rng = np.random.default_rng(SEED)

    def cen(idx):
        c = unit[idx].mean(axis=0)
        return c / np.linalg.norm(c)

    rows = []
    # 時間順とランダム順、両方の dist 系列を作る
    dist_t = np.zeros((len(pids), MAX_D))
    dist_r = np.zeros((len(pids), MAX_D))
    plen_t = np.zeros(len(pids)); plen_r = np.zeros(len(pids))
    cons_t = np.zeros(len(pids))

    for pi_, p in enumerate(pids):
        pc = cen(past[p])
        pool_all = np.array([i for d in range(1, MAX_D + 1) for i in fut[p][d]])
        dt = np.zeros((TRIALS, MAX_D)); dr = np.zeros((TRIALS, MAX_D))
        pl_t = np.zeros(TRIALS); pl_r = np.zeros(TRIALS); cs = np.zeros(TRIALS)
        for t in range(TRIALS):
            # --- 時間順: 各年から K 本 ---
            Ft = []
            for d in range(1, MAX_D + 1):
                arr = np.array(fut[p][d])
                Ft.append(cen(arr[rng.choice(len(arr), K, replace=False)].tolist()))
            Ft = np.stack(Ft)
            dt[t] = 1.0 - Ft @ pc
            pl_t[t] = sum(1.0 - float(Ft[d] @ Ft[d + 1]) for d in range(MAX_D - 1))
            disp = np.diff(np.vstack([pc, Ft]), axis=0)
            nn = np.linalg.norm(disp, axis=1, keepdims=True); nn[nn < 1e-12] = 1.0
            dn = disp / nn
            cs[t] = np.mean([dn[i] @ dn[i + 1] for i in range(len(dn) - 1)])
            # --- ランダム順: 年を無視して K 本ずつ MAX_D 回 ---
            Fr = []
            for _ in range(MAX_D):
                Fr.append(cen(pool_all[rng.choice(len(pool_all), K, replace=False)].tolist()))
            Fr = np.stack(Fr)
            dr[t] = 1.0 - Fr @ pc
            pl_r[t] = sum(1.0 - float(Fr[d] @ Fr[d + 1]) for d in range(MAX_D - 1))
        dist_t[pi_] = dt.mean(axis=0); dist_r[pi_] = dr.mean(axis=0)
        plen_t[pi_] = pl_t.mean(); plen_r[pi_] = pl_r.mean(); cons_t[pi_] = cs.mean()

    print("\n=== 1. 時間順 vs ランダム順（各年 K=3 本、10 試行の平均）===")
    print(f"  {'':<10}{'時間順':>12}{'ランダム順':>14}{'差':>10}")
    for d in range(MAX_D):
        print(f"  dist_{d+1:<5}{dist_t[:,d].mean():>12.4f}{dist_r[:,d].mean():>14.4f}"
              f"{dist_t[:,d].mean()-dist_r[:,d].mean():>+10.4f}")
    print(f"\n  ランダム順の dist は d によらずほぼ一定 → サンプル数の効果は消えている")

    inc_t = (dist_t[:, -1] > dist_t[:, 0])
    inc_r = (dist_r[:, -1] > dist_r[:, 0])
    print(f"\n=== 2. 「徐々に離れていく」か ===")
    print(f"  時間順   dist_5 > dist_1: {inc_t.mean()*100:>5.1f}%")
    print(f"  ランダム順 同          : {inc_r.mean()*100:>5.1f}%  ← 偶然なら 50%")
    mono_t = np.mean(np.diff(dist_t, axis=1) > 0, axis=1)
    mono_r = np.mean(np.diff(dist_r, axis=1) > 0, axis=1)
    print(f"  単調増加した区間の割合  時間順 {mono_t.mean():.3f} / ランダム順 {mono_r.mean():.3f}")
    st = wilcoxon(dist_t[:, -1], dist_t[:, 0])
    print(f"  dist_5 vs dist_1 の符号付き順位検定（時間順）: p = {st.pvalue:.3g}")

    print(f"\n=== 3. 経路長は時間順に固有か ===")
    print(f"  時間順 {plen_t.mean():.4f} / ランダム順 {plen_r.mean():.4f} "
          f"（比 {plen_t.mean()/plen_r.mean():.3f}）")
    sp = wilcoxon(plen_t, plen_r)
    print(f"  符号付き順位検定: p = {sp.pvalue:.3g}")
    print(f"  時間順 < ランダム順 の論文: {(plen_t < plen_r).mean()*100:.1f}%")

    # 既存指標との相関（サイズ依存も）
    def col(k, f=float):
        return np.array([f(base[p][k]) if base[p][k] else np.nan for p in pids])
    npast, nfut = col("n_past", int), col("n_future", int)
    dis, atyp, cit, mv = col("disruption"), col("Atyp_Median_Z"), col("citation_count", int), col("movement")
    dv = np.array([base[p]["d_valid"] == "true" for p in pids])
    slope = np.array([np.polyfit(np.arange(1, MAX_D+1), dist_t[i], 1)[0] for i in range(len(pids))])
    detour = plen_t / np.maximum(dist_t[:, -1], 1e-9)

    feats = {"動き（2点間）": mv, "離れ方の傾き": slope, "経路長（固定本数）": plen_t,
             "迂回度（固定本数）": detour, "方向の一貫性": cons_t, "単調性": mono_t}
    print(f"\n=== 4. サイズ依存性 ===")
    print(f"  {'':<22}{'× n_past':>11}{'× n_future':>12}")
    for nm, v in feats.items():
        m = ~np.isnan(v)
        print(f"  {nm:<22}{spearmanr(v[m], npast[m]).statistic:>11.3f}"
              f"{spearmanr(v[m], nfut[m]).statistic:>12.3f}")
    print(f"\n=== 5. 既存指標との相関 ===")
    print(f"  {'':<22}{'× disruption':>15}{'× Atyp':>11}{'× log(1+引用)':>15}{'× 動き':>10}")
    for nm, v in feats.items():
        m1 = dv & ~np.isnan(v); m2 = ~np.isnan(atyp) & ~np.isnan(v); m3 = ~np.isnan(v)
        print(f"  {nm:<22}{spearmanr(v[m1], dis[m1]).statistic:>15.4f}"
              f"{spearmanr(v[m2], atyp[m2]).statistic:>11.4f}"
              f"{spearmanr(v[m3], np.log1p(cit[m3])).statistic:>15.4f}"
              f"{spearmanr(v[m3], mv[m3]).statistic:>10.4f}")

    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["paperid"] + [f"dist_t{d+1}" for d in range(MAX_D)]
                   + [f"dist_r{d+1}" for d in range(MAX_D)]
                   + ["slope", "path_len_t", "path_len_r", "detour", "consistency", "monotonic"])
        for i, p in enumerate(pids):
            w.writerow([p] + [f"{x:.6f}" for x in dist_t[i]] + [f"{x:.6f}" for x in dist_r[i]]
                       + [f"{slope[i]:.8f}", f"{plen_t[i]:.6f}", f"{plen_r[i]:.6f}",
                          f"{detour[i]:.6f}", f"{cons_t[i]:.6f}", f"{mono_t[i]:.4f}"])
    print(f"\n保存: {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
