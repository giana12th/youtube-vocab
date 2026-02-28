"""YouTube字幕取得モジュール。

YouTube URLから英語字幕を取得し、output/{session_id}_source.txt に保存する。
"""

import sys
from datetime import date
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from youtube_transcript_api import YouTubeTranscriptApi


def _extract_video_id(url: str) -> str:
    """URLからYouTube動画IDを抽出する。

    youtube.com/watch?v=ID と youtu.be/ID の両方に対応。
    """
    parsed = urlparse(url)
    if parsed.hostname in ("www.youtube.com", "youtube.com", "m.youtube.com"):
        qs = parse_qs(parsed.query)
        if "v" in qs:
            return qs["v"][0]
    if parsed.hostname in ("youtu.be",):
        return parsed.path.lstrip("/")
    raise ValueError(f"YouTube動画IDを抽出できません: {url}")


def run(url: str) -> str:
    """YouTube URLから字幕を取得し、_source.txtに保存する。

    Args:
        url: YouTube動画のURL

    Returns:
        セッションID（{YYYYMMDD}_{video_id}）
    """
    video_id = _extract_video_id(url)
    today = date.today().strftime("%Y%m%d")
    session_id = f"{today}_{video_id}"

    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / f"{session_id}_source.txt"

    if output_path.exists():
        print(f"[SKIP] subtitle.py: {output_path} は既に存在します")
        return session_id

    print(f"[INFO] subtitle.py: 字幕を取得中... ({video_id})")

    try:
        ytt_api = YouTubeTranscriptApi()
        fetched = ytt_api.fetch(video_id, languages=["en"])
    except Exception as e:
        print(f"[ERROR] subtitle.py: 英語字幕が見つかりません: {e}", file=sys.stderr)
        sys.exit(1)

    # snippet.text の改行を空白に置換してから結合
    lines = []
    for snippet in fetched:
        text = snippet.text.replace("\n", " ")
        lines.append(text)
    content = "\r\n".join(lines)

    output_path.write_text(content, encoding="utf-8", newline="")
    print(f"[INFO] subtitle.py: {output_path} に保存しました")
    return session_id


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: uv run subtitle.py <YouTube URL>", file=sys.stderr)
        sys.exit(1)
    session_id = run(sys.argv[1])
    print(f"Session ID: {session_id}")
