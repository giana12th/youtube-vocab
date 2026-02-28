"""単語抽出モジュール。

_source.txt からspaCyで品詞解析し、学習対象の単語を抽出して _wordlist.json に保存する。
"""

import json
import sys
from pathlib import Path

import spacy
from wordfreq import zipf_frequency

import config
from util import detect_latest_session

TARGET_POS = {"ADJ", "ADV", "VERB"}
POS_PRIORITY = {"ADJ": 0, "ADV": 1, "VERB": 2}
MAX_WORDS = 20


def run(session_id: str) -> None:
    """_source.txt から単語を抽出し、_wordlist.json に保存する。

    Args:
        session_id: セッションID
    """
    output_dir = Path("output")
    source_path = output_dir / f"{session_id}_source.txt"
    wordlist_path = output_dir / f"{session_id}_wordlist.json"

    if not source_path.exists():
        print(
            f"[ERROR] extractor.py: source.txt が見つかりません: {source_path}",
            file=sys.stderr,
        )
        sys.exit(1)

    print("[INFO] extractor.py: 単語を抽出中...")

    text = source_path.read_text(encoding="utf-8")
    nlp = spacy.load("en_core_web_sm")
    doc = nlp(text)

    # lemma をキーに重複排除（最初の出現文を採用）
    seen: dict[str, dict] = {}
    zipf_threshold = float(config.zipf)

    for token in doc:
        if token.pos_ not in TARGET_POS:
            continue
        lemma = token.lemma_.lower()
        if lemma in seen:
            continue
        zf = zipf_frequency(lemma, "en")
        if zf >= zipf_threshold:
            continue
        sentence = token.sent.text.strip()
        seen[lemma] = {
            "word": lemma,
            "pos": token.pos_,
            "sentence": sentence,
            "_zipf": zf,
            "_order": len(seen),
        }

    candidates = list(seen.values())

    # 20件超の場合: 品詞優先(ADJ>ADV>VERB) → zipf昇順 → 出現順
    if len(candidates) > MAX_WORDS:
        candidates.sort(
            key=lambda w: (POS_PRIORITY[w["pos"]], w["_zipf"], w["_order"])
        )
        candidates = candidates[:MAX_WORDS]

    # 内部用フィールドを除去
    wordlist = [
        {"word": w["word"], "pos": w["pos"], "sentence": w["sentence"]}
        for w in candidates
    ]

    wordlist_path.write_text(
        json.dumps(wordlist, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[INFO] extractor.py: {len(wordlist)} 件の単語を抽出しました → {wordlist_path}")


if __name__ == "__main__":
    if len(sys.argv) >= 2:
        sid = sys.argv[1]
    else:
        sid = detect_latest_session()
    run(sid)
