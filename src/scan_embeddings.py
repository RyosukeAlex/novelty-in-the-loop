"""GCS の SPECTER2 埋め込み 112 ファイルを走査し、必要な論文の分だけ抜き出す。

**US リージョンの VM 上で実行すること。** ローカルから実行するとインターネット egress が
発生し、1.62TiB で $190〜220 かかる（docs/tasks/003-embedding-extraction.md §3）。

使い方（VM 上）:
    # まず 1 ファイルだけ処理して課金を確認する
    python3 scan_embeddings.py --files 0 --out /mnt/out

    # 問題なければ残りを並列で
    python3 scan_embeddings.py --files 1-111 --out /mnt/out --workers 8

速度の鍵:
    ヒット率は 499,727 / 約1.17億 = 0.43%。1 行 15KB を全部 JSON パースすると
    768 個の float 変換が走って数十時間かかる。行の先頭 30 バイトに paperid があるので
    そこだけ文字列で判定し、ヒットした行だけパースする。
"""

import argparse
import csv
import io
import json
import multiprocessing as mp
import os
import pathlib
import sys
import time

import numpy as np
import orjson
from google.cloud import storage

SRC_BUCKET = "sciscinet-neo"
SRC_PREFIX = "v2/embeddings/sciscinet_emb_chunk_"
PREFIX_LEN = len('{"paperid": "')      # 行の先頭。ここから paperid が始まる
DIM = 768

_TARGETS: set[str] = set()              # 子プロセスが fork で共有する


def load_targets(path: str) -> set[str]:
    with open(path, newline="", encoding="utf-8") as f:
        return {row["paperid"] for row in csv.DictReader(f)}


def parse_file_spec(spec: str) -> list[int]:
    out: list[int] = []
    for part in spec.split(","):
        if "-" in part:
            a, b = part.split("-")
            out.extend(range(int(a), int(b) + 1))
        else:
            out.append(int(part))
    return sorted(set(out))


def scan_one(args: tuple[int, str]) -> tuple[int, int, int, float]:
    """1 ファイルを走査して (ファイル番号, 走査行数, ヒット数, 秒) を返す。"""
    idx, out_dir = args
    name = f"{SRC_PREFIX}{idx:04d}.jsonl"
    vec_path = pathlib.Path(out_dir) / f"chunk_{idx:04d}.npy"
    ids_path = pathlib.Path(out_dir) / f"chunk_{idx:04d}.ids.txt"
    done_path = pathlib.Path(out_dir) / f"chunk_{idx:04d}.done"

    if done_path.exists():          # 再開時は処理済みを飛ばす
        return (idx, 0, 0, 0.0)

    t0 = time.time()
    client = storage.Client()
    blob = client.bucket(SRC_BUCKET).blob(name)

    ids: list[str] = []
    vecs: list[np.ndarray] = []
    n_lines = 0

    with blob.open("rt", chunk_size=32 * 1024 * 1024) as f:
        for line in f:
            n_lines += 1
            # 先頭が想定の形なら固定オフセットで切る。ID は 10〜11 桁で可変なので
            # 終端のクォートを探す（固定長で切ってはいけない）。
            if line.startswith('{"paperid": "'):
                end = line.find('"', PREFIX_LEN)
                pid = line[PREFIX_LEN:end]
            else:
                # 形式が違う行はここで初めて JSON として読む（想定外の保険）
                try:
                    pid = orjson.loads(line)["paperid"]
                except Exception:
                    continue
            if pid not in _TARGETS:
                continue
            try:
                rec = orjson.loads(line)
            except Exception:
                continue
            emb = rec.get("embedding")
            if not emb or len(emb) != DIM:
                continue
            ids.append(pid)
            vecs.append(np.asarray(emb, dtype=np.float32))

    arr = np.stack(vecs) if vecs else np.empty((0, DIM), dtype=np.float32)
    np.save(vec_path, arr)
    ids_path.write_text("\n".join(ids), encoding="utf-8")
    done_path.write_text(json.dumps({"lines": n_lines, "hits": len(ids)}), encoding="utf-8")
    return (idx, n_lines, len(ids), time.time() - t0)


def init_worker(targets: set[str]) -> None:
    global _TARGETS
    _TARGETS = targets


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--targets", default="paperids.csv", help="paperid の CSV（header 付き）")
    ap.add_argument("--files", default="0", help="処理するファイル番号。例: 0 / 1-111 / 0,5,9")
    ap.add_argument("--out", required=True, help="出力ディレクトリ")
    ap.add_argument("--workers", type=int, default=1)
    args = ap.parse_args()

    pathlib.Path(args.out).mkdir(parents=True, exist_ok=True)
    targets = load_targets(args.targets)
    files = parse_file_spec(args.files)
    print(f"対象 paperid {len(targets)} 件 / 走査ファイル {len(files)} 本 / 並列 {args.workers}",
          flush=True)

    t0 = time.time()
    tot_lines = tot_hits = 0
    jobs = [(i, args.out) for i in files]

    if args.workers <= 1:
        init_worker(targets)
        results = map(scan_one, jobs)
    else:
        pool = mp.Pool(args.workers, initializer=init_worker, initargs=(targets,))
        results = pool.imap_unordered(scan_one, jobs)

    for idx, n_lines, hits, sec in results:
        tot_lines += n_lines
        tot_hits += hits
        if n_lines:
            print(f"  chunk_{idx:04d}: {n_lines:>9} 行 / ヒット {hits:>6} / {sec:>6.1f}秒",
                  flush=True)
        else:
            print(f"  chunk_{idx:04d}: 済み（スキップ）", flush=True)

    el = time.time() - t0
    print(f"\n完了: {tot_lines} 行走査 / {tot_hits} 件取得 / {el:.1f}秒")
    if tot_lines:
        print(f"  ヒット率 {100*tot_hits/tot_lines:.3f}%  "
              f"速度 {tot_lines/el:,.0f} 行/秒")
        remaining = 112 - len(files)
        if remaining > 0:
            print(f"  残り {remaining} ファイルの推定時間: {el/len(files)*remaining/60:.1f} 分"
                  f"（同じ並列度なら）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
