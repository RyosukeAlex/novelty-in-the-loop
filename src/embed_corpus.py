"""SPECTER2 でコーパスの埋め込みを計算し、.npy と paperid リストに保存する。

使い方:
    uv run python src/embed_corpus.py data/engine/corpus_text.jsonl data/engine/corpus_emb

出力:
    <out>.npy        float32 の (N, 768)。L2 正規化はしない（SciSciNet の形式に揃える）
    <out>_ids.json   npy の行に対応する paperid のリスト + 統計

なぜ正規化しないか:
    SciSciNet-v2 の埋め込みも正規化されていない（ノルム約 21.5）。
    正規化は使う側で行う。保存時に落とすと元に戻せない。
"""

import argparse
import json
import pathlib
import sys

import numpy as np
import torch
from adapters import AutoAdapterModel
from transformers import AutoTokenizer

MODEL = "allenai/specter2_base"
ADAPTER = "allenai/specter2"


def pick_device() -> str:
    if torch.backends.mps.is_available():
        return "mps"
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("text_jsonl")
    ap.add_argument("out_prefix")
    ap.add_argument("--batch", type=int, default=32)
    ap.add_argument("--max-length", type=int, default=512)
    args = ap.parse_args()

    # 読み込みと整形。title が無い論文は埋め込めないので落とす。
    records, no_title, no_abstract = [], 0, 0
    with open(args.text_jsonl, encoding="utf-8") as f:
        for line in f:
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not r.get("title"):
                no_title += 1
                continue
            if not r.get("abstract"):
                no_abstract += 1
            records.append(r)

    # 同じ paperid が二重に入っていたら後のものを捨てる（再実行で追記されるため）
    seen, uniq = set(), []
    for r in records:
        if r["paperid"] not in seen:
            seen.add(r["paperid"])
            uniq.append(r)
    records = uniq

    print(f"埋め込み対象 {len(records)} 件 / title なし {no_title} 件 / 要旨なし {no_abstract} 件",
          flush=True)
    if not records:
        return 1

    device = pick_device()
    print(f"デバイス: {device}", flush=True)

    tok = AutoTokenizer.from_pretrained(MODEL)
    model = AutoAdapterModel.from_pretrained(MODEL)
    model.load_adapter(ADAPTER, source="hf", load_as="proximity", set_active=True)
    model.to(device).eval()

    # SPECTER2 の標準入力は title + [SEP] + abstract。要旨が無ければ title だけ。
    texts = [
        r["title"] + (tok.sep_token + r["abstract"] if r.get("abstract") else "")
        for r in records
    ]

    vecs = np.empty((len(texts), 768), dtype=np.float32)
    with torch.no_grad():
        for i in range(0, len(texts), args.batch):
            batch = tok(texts[i:i + args.batch], padding=True, truncation=True,
                        return_tensors="pt", max_length=args.max_length).to(device)
            out = model(**batch)
            # 文書ベクトルは CLS トークン（先頭）の最終隠れ状態
            vecs[i:i + args.batch] = out.last_hidden_state[:, 0, :].cpu().numpy()
            if (i // args.batch) % 50 == 0:
                print(f"  {min(i + args.batch, len(texts))}/{len(texts)}", flush=True)

    out_prefix = pathlib.Path(args.out_prefix)
    out_prefix.parent.mkdir(parents=True, exist_ok=True)
    np.save(out_prefix.with_suffix(".npy"), vecs)

    norms = np.linalg.norm(vecs, axis=1)
    meta = {
        "model": MODEL,
        "adapter": ADAPTER,
        "normalized": False,
        "paperids": [r["paperid"] for r in records],
        "n": len(records),
        "no_abstract": no_abstract,
        "norm_mean": float(norms.mean()),
        "norm_std": float(norms.std()),
    }
    with open(str(out_prefix) + "_ids.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False)

    # SciSciNet の埋め込みはノルム約 21.5。大きく違えば入力形式かアダプタがずれている。
    print(f"完了: {vecs.shape}  ノルム平均 {norms.mean():.2f} (±{norms.std():.2f})")
    print(f"  → SciSciNet の報告値は約 21.5（docs/tasks/002）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
