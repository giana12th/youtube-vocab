"""エントリーポイント。

YouTube URLまたはテキストファイルを受け取り、
字幕取得→単語抽出→クイズ生成→クイズ実行のパイプラインを実行する。
"""

import sys
from pathlib import Path

import extractor
import explainer
import quiz
import source
import subtitle


def main() -> None:
    """メインのパイプライン実行関数。"""
    if len(sys.argv) < 2:
        print(
            "Usage: uv run main.py <YouTube URL or text file>",
            file=sys.stderr,
        )
        sys.exit(1)

    arg = sys.argv[1]

    # 入力種別の判定
    if arg.startswith("http://") or arg.startswith("https://"):
        if "youtube.com" in arg or "youtu.be" in arg:
            session_id = subtitle.run(arg)
        else:
            print(
                f"[ERROR] main.py: YouTube以外のURLはサポートしていません: {arg}",
                file=sys.stderr,
            )
            sys.exit(1)
    else:
        if not Path(arg).exists():
            print(
                f"[ERROR] main.py: ファイルが見つかりません: {arg}",
                file=sys.stderr,
            )
            sys.exit(1)
        session_id = source.run(arg)

    # パイプライン実行
    extractor.run(session_id)
    explainer.run(session_id)
    quiz.run(session_id)


if __name__ == "__main__":
    main()
