"""OpenAlex からタイトルと要旨を取得して JSONL に保存する。

使い方:
    uv run python src/fetch_openalex.py data/engine/corpus_ids.csv data/engine/corpus_text.jsonl
    uv run python src/fetch_openalex.py ... --mailto you@example.com   # polite pool（10 req/s）

中断しても再実行すれば続きから取得する（出力 JSONL に入っている paperid を飛ばす）。
"""

import argparse
import csv
import json
import pathlib
import sys
import time

import httpx

API = "https://api.openalex.org/works"
BATCH = 50          # OpenAlex が 1 回の OR フィルタで受け付ける ID の上限
FIELDS = "id,title,abstract_inverted_index,publication_year,type"


def restore_abstract(inverted: dict | None) -> str | None:
    """転置インデックス {語: [位置...]} を元の文章に戻す。

    OpenAlex は要旨を「どの語が何文字目に出たか」の形で持っている。
    位置をキーにして並べ直し、空白でつなげば元の文に戻る。
    語には句読点が含まれている（"technician," など）ので、区切りは空白だけでよい。
    """
    if not inverted:
        return None
    by_pos: dict[int, str] = {}
    for word, positions in inverted.items():
        for p in positions:
            by_pos[p] = word
    return " ".join(by_pos[p] for p in sorted(by_pos))


def load_done(out_path: pathlib.Path) -> set[str]:
    """すでに取得済みの paperid を読む（再開用）。"""
    if not out_path.exists():
        return set()
    done = set()
    with out_path.open(encoding="utf-8") as f:
        for line in f:
            try:
                done.add(json.loads(line)["paperid"])
            except (json.JSONDecodeError, KeyError):
                continue    # 途中で切れた最終行は捨てる
    return done


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("ids_csv")
    ap.add_argument("out_jsonl")
    ap.add_argument("--mailto", default=None, help="OpenAlex の polite pool を使う場合のみ")
    ap.add_argument("--sleep", type=float, default=0.12, help="リクエスト間隔（秒）")
    args = ap.parse_args()

    out_path = pathlib.Path(args.out_jsonl)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with open(args.ids_csv, encoding="utf-8") as f:
        all_ids = [row["paperid"] for row in csv.DictReader(f)]

    done = load_done(out_path)
    todo = [i for i in all_ids if i not in done]
    print(f"全 {len(all_ids)} 件 / 取得済み {len(done)} 件 / 残り {len(todo)} 件", flush=True)
    if not todo:
        return 0

    params_base = {"select": FIELDS, "per-page": str(BATCH)}
    if args.mailto:
        params_base["mailto"] = args.mailto

    n_ok = n_miss = n_noabs = 0
    with httpx.Client(timeout=60.0) as client, out_path.open("a", encoding="utf-8") as out:
        for start in range(0, len(todo), BATCH):
            chunk = todo[start:start + BATCH]
            params = dict(params_base, filter="openalex:" + "|".join(chunk))

            for attempt in range(4):        # 429 / 一時障害は待って再試行
                try:
                    r = client.get(API, params=params)
                    if r.status_code == 200:
                        break
                    if r.status_code in (429, 500, 502, 503, 504):
                        time.sleep(2 ** attempt)
                        continue
                    print(f"  HTTP {r.status_code}: {r.text[:200]}", file=sys.stderr)
                    return 1
                except httpx.RequestError as e:
                    if attempt == 3:
                        print(f"  通信エラー: {e}", file=sys.stderr)
                        return 1
                    time.sleep(2 ** attempt)
            else:
                print("  再試行の上限に達した", file=sys.stderr)
                return 1

            got = set()
            for w in r.json().get("results", []):
                pid = w["id"].rsplit("/", 1)[-1]        # URL 形式 → W... に直す
                got.add(pid)
                abstract = restore_abstract(w.get("abstract_inverted_index"))
                if abstract is None:
                    n_noabs += 1
                out.write(json.dumps({
                    "paperid": pid,
                    "title": w.get("title"),
                    "abstract": abstract,
                    "year": w.get("publication_year"),
                    "type": w.get("type"),
                }, ensure_ascii=False) + "\n")
                n_ok += 1
            # OpenAlex に無い ID も記録する（後で欠損の偏りを見るため）
            for pid in set(chunk) - got:
                out.write(json.dumps({"paperid": pid, "title": None, "abstract": None,
                                      "year": None, "type": None}) + "\n")
                n_miss += 1

            out.flush()
            if (start // BATCH) % 20 == 0:
                print(f"  {start + len(chunk)}/{len(todo)}  取得 {n_ok} / 不在 {n_miss} / 要旨なし {n_noabs}",
                      flush=True)
            time.sleep(args.sleep)

    print(f"完了: 取得 {n_ok} / OpenAlex に不在 {n_miss} / 要旨なし {n_noabs}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
