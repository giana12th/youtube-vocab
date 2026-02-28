"""Claude連携・クイズJSON生成モジュール。

_wordlist.json からプロンプトを生成し、claude -p で日本語訳・誤答を取得して
_quiz.json に保存する。
"""

import json
import random
import re
import shutil
import subprocess
import sys
from pathlib import Path

from util import detect_latest_session

INSTRUCTIONS_TEMPLATE = """\
## Instructions

You are an English vocabulary assistant for Japanese learners.

Given a list of English words with their part of speech (pos) and example sentences,
output a JSON array where each item contains:
- "word": the English word (same as input)
- "correct": the Japanese translation
- "distractors": exactly 3 Japanese translations that are plausible but incorrect

Rules for "correct":
- Translate based on how the word is used in the given sentence
- Use natural Japanese (not overly literal)
- Keep it concise: aim for 2-6 characters

Rules for "distractors":
- Each distractor must be a real Japanese word or phrase
- Use the pos field to constrain distractor types:
  - ADJ → other Japanese adjectives (い形容詞 or な形容詞)
  - ADV → other Japanese adverbs or adverbial phrases
  - VERB → other Japanese verbs or verb phrases
- Choose distractors that are semantically close or commonly confused with the correct answer
- All 4 options (correct + 3 distractors) must be clearly distinct from each other
- Do NOT use antonyms as distractors unless they are genuinely confusable

Output format:
- JSON array ONLY
- No markdown, no code fences, no preamble, no explanation
- One object per word, in the same order as the input"""


def _parse_claude_output(raw: str) -> list:
    """Claudeの出力を3段階フォールバックでJSONパースする。

    Args:
        raw: Claudeの標準出力

    Returns:
        パースされたJSONリスト

    Raises:
        ValueError: パース失敗時
    """
    # 1. そのままパース
    try:
        return json.loads(raw.strip())
    except json.JSONDecodeError:
        pass

    # 2. ```json ... ``` ブロックの抽出
    match = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # 3. [ ... ] の最初のブロックを抽出
    match = re.search(r"(\[.*\])", raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    raise ValueError("Claudeのレスポンスを JSON としてパースできませんでした。")


def run(session_id: str) -> None:
    """_wordlist.json からクイズデータを生成し、_quiz.json に保存する。

    Args:
        session_id: セッションID
    """
    output_dir = Path("output")
    wordlist_path = output_dir / f"{session_id}_wordlist.json"
    prompt_path = output_dir / f"{session_id}_prompt.md"
    quiz_path = output_dir / f"{session_id}_quiz.json"

    if not wordlist_path.exists():
        print(
            f"[ERROR] explainer.py: wordlist.json が見つかりません: {wordlist_path}",
            file=sys.stderr,
        )
        sys.exit(1)

    # claude コマンドの存在チェック
    if shutil.which("claude") is None:
        print(
            "[ERROR] explainer.py: claude コマンドが見つかりません。"
            "Claude Code がインストールされているか確認してください。",
            file=sys.stderr,
        )
        sys.exit(1)

    wordlist_text = wordlist_path.read_text(encoding="utf-8")
    wordlist = json.loads(wordlist_text)

    # プロンプト生成
    prompt_text = f"{INSTRUCTIONS_TEMPLATE}\n\n## Word List\n\n{wordlist_text}"
    prompt_path.write_text(prompt_text, encoding="utf-8")
    print(f"[INFO] explainer.py: プロンプトを保存しました → {prompt_path}")

    # Claude 呼び出し
    print("[INFO] explainer.py: Claude を呼び出し中...")
    result = subprocess.run(
        ["claude", "-p"],
        input=prompt_text,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print(
            f"[ERROR] explainer.py: claude コマンドがエラーで終了しました: {result.stderr}",
            file=sys.stderr,
        )
        sys.exit(1)

    raw_output = result.stdout

    # パース
    try:
        claude_data = _parse_claude_output(raw_output)
    except ValueError as e:
        raw_path = output_dir / f"{session_id}_claude_raw.txt"
        raw_path.write_text(raw_output, encoding="utf-8")
        print(f"[ERROR] explainer.py: {e}", file=sys.stderr)
        print(
            f"[ERROR] explainer.py: raw output を {raw_path} に保存しました。",
            file=sys.stderr,
        )
        sys.exit(1)

    # wordlist を辞書化（word → {sentence, pos}）
    word_info = {item["word"]: item for item in wordlist}

    # バリデーション & quiz.json 構築
    total = len(wordlist)
    if len(claude_data) != total:
        print(
            f"[WARN] explainer.py: 配列の長さが一致しません（期待: {total}, 実際: {len(claude_data)}）"
        )

    valid_entries = []
    for entry in claude_data:
        word = entry.get("word")
        correct = entry.get("correct")
        distractors = entry.get("distractors")

        # キー存在チェック
        if not all([word, correct, distractors]):
            print(f"[WARN] explainer.py: 必須キーが不足しています: {entry}")
            continue

        # wordlist にない単語はスキップ
        if word not in word_info:
            print(f"[WARN] explainer.py: wordlist に存在しない単語です: {word}")
            continue

        # distractors 数チェック
        if not isinstance(distractors, list) or len(distractors) != 3:
            print(f"[WARN] explainer.py: distractors が3つではありません: {word}")
            continue

        # correct が distractors に含まれていないかチェック
        if correct in distractors:
            print(f"[WARN] explainer.py: correct が distractors に重複しています: {word}")
            continue

        # choices をシャッフル
        choices = [correct] + distractors
        random.shuffle(choices)

        valid_entries.append({
            "word": word,
            "sentence": word_info[word]["sentence"],
            "correct": correct,
            "choices": choices,
        })

    # 有効エントリが50%未満ならエラー
    if len(valid_entries) < total * 0.5:
        print(
            f"[ERROR] explainer.py: 有効なエントリが少なすぎます"
            f"（{len(valid_entries)}/{total}件）。explainer.py を再実行してください。",
            file=sys.stderr,
        )
        sys.exit(1)

    quiz_path.write_text(
        json.dumps(valid_entries, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[INFO] explainer.py: {len(valid_entries)} 件のクイズを生成しました → {quiz_path}")


if __name__ == "__main__":
    if len(sys.argv) >= 2:
        sid = sys.argv[1]
    else:
        sid = detect_latest_session()
    run(sid)
