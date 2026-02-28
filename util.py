"""共通ユーティリティ。"""

from pathlib import Path


def detect_latest_session() -> str:
    """output/ 内の最新セッションIDを自動検出する。

    _source.txt のファイル名から日付部分を取得し、
    日付+mtimeソートで最新を返す。

    Returns:
        最新のセッションID

    Raises:
        FileNotFoundError: セッションが見つからない場合
    """
    output_dir = Path("output")
    files = list(output_dir.glob("*_source.txt"))
    if not files:
        raise FileNotFoundError("output/ にセッションが見つかりません")
    files.sort(key=lambda f: (f.name[:8], f.stat().st_mtime), reverse=True)
    return files[0].name.replace("_source.txt", "")
