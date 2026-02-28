"""テキストファイル取り込みモジュール。

任意のテキストファイルを読み込み、output/{session_id}_source.txt に保存する。
"""

import sys
from datetime import date
from pathlib import Path


def run(filepath: str) -> str:
    """テキストファイルを読み込み、_source.txtに保存する。

    Args:
        filepath: 入力テキストファイルのパス

    Returns:
        セッションID（{YYYYMMDD}_{stem[:20]}）
    """
    src = Path(filepath)
    if not src.exists():
        print(f"[ERROR] source.py: ファイルが見つかりません: {filepath}", file=sys.stderr)
        sys.exit(1)

    stem = src.stem[:20]
    today = date.today().strftime("%Y%m%d")
    session_id = f"{today}_{stem}"

    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / f"{session_id}_source.txt"

    if output_path.exists():
        print(f"[SKIP] source.py: {output_path} は既に存在します")
        return session_id

    print(f"[INFO] source.py: {filepath} を読み込み中...")

    # UTF-8-sig でBOM付きにも対応、デコードエラーは置換
    content = src.read_text(encoding="utf-8-sig", errors="replace")
    # 置換文字 U+FFFD を ? に変換
    content = content.replace("\ufffd", "?")
    # CRLF に統一
    content = content.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "\r\n")

    output_path.write_text(content, encoding="utf-8", newline="")
    print(f"[INFO] source.py: {output_path} に保存しました")
    return session_id


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: uv run source.py <text file>", file=sys.stderr)
        sys.exit(1)
    session_id = run(sys.argv[1])
    print(f"Session ID: {session_id}")
