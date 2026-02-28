"""クイズ実行・結果出力モジュール。

_quiz.json を読み込み、ターミナルで4択クイズを実行し、
_quiz_result.csv と _wordlist.md を出力する。
"""

import csv
import io
import json
import random
import sys
from pathlib import Path


def _detect_latest_session() -> str:
    """output/ 内の最新セッションIDを自動検出する。"""
    output_dir = Path("output")
    files = list(output_dir.glob("*_source.txt"))
    if not files:
        raise FileNotFoundError("output/ にセッションが見つかりません")
    files.sort(key=lambda f: (f.name[:8], f.stat().st_mtime), reverse=True)
    return files[0].name.replace("_source.txt", "")


def _run_quiz(questions: list) -> list[dict]:
    """ターミナルでクイズを実行する。

    Args:
        questions: quiz.json のエントリリスト（シャッフル済み）

    Returns:
        不正解の単語情報リスト

    Raises:
        KeyboardInterrupt: Ctrl+C で中断時
    """
    total = len(questions)
    incorrect: list[dict] = []

    for i, q in enumerate(questions, 1):
        print()
        print("━" * 40)
        print(f"Q{i} / {total}")
        print()
        print(f'"{q["sentence"]}"')
        print()
        print(f'👉 "{q["word"]}" の意味は？')
        print()
        for j, choice in enumerate(q["choices"], 1):
            print(f"  {j}. {choice}")
        print("━" * 40)

        # 入力受付: 1-4 のみ
        while True:
            answer = input("\n> ").strip()
            if answer in ("1", "2", "3", "4"):
                break
            print("1〜4 の数字を入力してください。")

        selected = q["choices"][int(answer) - 1]
        if selected == q["correct"]:
            print("✅ 正解！")
        else:
            print(f"❌ 不正解… 正解は「{q['correct']}」")
            incorrect.append(q)

    return incorrect


def _write_csv(session_id: str, incorrect: list[dict], word_pos: dict[str, str]) -> None:
    """不正解の単語を _quiz_result.csv に書き出す。

    Args:
        session_id: セッションID
        incorrect: 不正解のクイズエントリリスト
        word_pos: 単語→品詞の辞書
    """
    output_path = Path("output") / f"{session_id}_quiz_result.csv"

    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(["word", "pos", "correct", "sentence"])

    # 重複排除（同一単語が複数回出ることはないはずだが念のため）
    seen: set[str] = set()
    for q in incorrect:
        if q["word"] not in seen:
            seen.add(q["word"])
            writer.writerow([
                q["word"],
                word_pos.get(q["word"], ""),
                q["correct"],
                q["sentence"],
            ])

    output_path.write_text(buf.getvalue(), encoding="utf-8", newline="")
    print(f"[INFO] quiz.py: 不正解 {len(seen)} 件 → {output_path}")


def _write_wordlist_md(
    session_id: str,
    questions: list[dict],
    word_pos: dict[str, str],
) -> None:
    """全単語を品詞別に整理した _wordlist.md を書き出す。

    Args:
        session_id: セッションID
        questions: 全クイズエントリ
        word_pos: 単語→品詞の辞書
    """
    output_path = Path("output") / f"{session_id}_wordlist.md"

    # セッションIDからid部分を取得（日付_id）
    parts = session_id.split("_", 1)
    date_str = parts[0]
    id_part = parts[1] if len(parts) > 1 else session_id
    formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"

    # 品詞ごとにグループ化
    pos_groups: dict[str, list[dict]] = {"ADJ": [], "ADV": [], "VERB": []}
    for q in questions:
        pos = word_pos.get(q["word"], "VERB")
        if pos in pos_groups:
            pos_groups[pos].append(q)

    # 品詞内をアルファベット順にソート
    for entries in pos_groups.values():
        entries.sort(key=lambda e: e["word"])

    pos_labels = {"ADJ": "ADJ（形容詞）", "ADV": "ADV（副詞）", "VERB": "VERB（動詞）"}

    lines = [
        f"# 単語リスト：{id_part}",
        f"{formatted_date}",
        "",
        "---",
    ]

    for pos in ("ADJ", "ADV", "VERB"):
        entries = pos_groups[pos]
        if not entries:
            continue
        lines.append("")
        lines.append(f"## {pos_labels[pos]}")
        for entry in entries:
            lines.append("")
            lines.append(f"### {entry['word']}")
            lines.append(f"- **意味**：{entry['correct']}")
            lines.append(f"- **例文**：{entry['sentence']}")

    lines.append("")  # 末尾改行
    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[INFO] quiz.py: 単語リスト → {output_path}")


def run(session_id: str) -> None:
    """クイズを実行し、結果を出力する。

    Args:
        session_id: セッションID
    """
    output_dir = Path("output")
    quiz_path = output_dir / f"{session_id}_quiz.json"
    wordlist_path = output_dir / f"{session_id}_wordlist.json"

    if not quiz_path.exists():
        print(
            f"[ERROR] quiz.py: quiz.json が見つかりません: {quiz_path}",
            file=sys.stderr,
        )
        sys.exit(1)

    questions = json.loads(quiz_path.read_text(encoding="utf-8"))

    # _wordlist.json から品詞情報を取得
    word_pos: dict[str, str] = {}
    if wordlist_path.exists():
        wordlist = json.loads(wordlist_path.read_text(encoding="utf-8"))
        word_pos = {item["word"]: item["pos"] for item in wordlist}

    # 問題順シャッフル（choices はそのまま）
    random.shuffle(questions)

    print(f"\n📝 クイズ開始！（全{len(questions)}問）")

    try:
        incorrect = _run_quiz(questions)
    except KeyboardInterrupt:
        print("\n\n中断しました。結果は保存されません。")
        return

    # 結果表示
    correct_count = len(questions) - len(incorrect)
    print()
    print("=" * 40)
    print(f"結果：{correct_count} / {len(questions)} 問正解")
    print("=" * 40)

    # ファイル出力
    _write_csv(session_id, incorrect, word_pos)
    _write_wordlist_md(session_id, questions, word_pos)


if __name__ == "__main__":
    if len(sys.argv) >= 2:
        sid = sys.argv[1]
    else:
        sid = _detect_latest_session()
    run(sid)
