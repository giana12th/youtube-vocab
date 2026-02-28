# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

YouTube英語字幕 単語学習システム — A CLI tool that fetches YouTube subtitles, extracts vocabulary, generates Japanese quiz questions via Claude, and runs a terminal quiz.

## Commands

Run all scripts with `uv run`:

```bash
# Full pipeline (YouTube URL or text file)
uv run main.py https://youtube.com/watch?v=VIDEO_ID
uv run main.py my_article.txt

# Run individual steps (auto-detects latest session if no session ID given)
uv run subtitle.py https://youtube.com/watch?v=VIDEO_ID
uv run source.py my_article.txt
uv run extractor.py [session_id]
uv run explainer.py [session_id]
uv run quiz.py [session_id]
```

No automated tests — verify by running each step manually against real data.


## Architecture

5-step pipeline with loosely coupled scripts that communicate via files in `output/`:

| Step | Script | Input | Output |
|---|---|---|---|
| 1a | `subtitle.py` | YouTube URL | `_source.txt` |
| 1b | `source.py` | text file path | `_source.txt` |
| 2 | `extractor.py` | `_source.txt` | `_wordlist.json` |
| 3 | `explainer.py` | `_wordlist.json` | `_prompt.md`, `_quiz.json` |
| 4 | `quiz.py` | `_quiz.json` | `_quiz_result.csv`, `_wordlist.md` |

`main.py` imports each module and calls `run(session_id)`. Steps 2–4 use a common `run(session_id: str) -> None` interface; steps 1a/1b return the session ID.

### Session ID

Format: `{YYYYMMDD}_{id}` (e.g., `20260228_ZY34OTV30Ck`)
- YouTube URL → video ID extracted via `urllib.parse`
- Text file → `Path(filepath).stem` (truncated to 20 chars)

All intermediate files live in `output/` with this prefix.

### Key Design Points

- `_source.txt` is skipped (not regenerated) if it already exists; steps 2–4 always regenerate
- `extractor.py` filters to ADJ/ADV/VERB with `zipf_frequency < 4.0`, capped at 20 words. The zipf threshold is configured in `config.py`
- `explainer.py` calls `claude -p` via `subprocess.run(..., input=prompt_text)` (stdin, not shell args). Prompt is saved to `_prompt.md` for debugging
- Claude's JSON response uses 3-stage fallback parsing (`json.loads` → extract from ` ```json ``` ` → extract `[...]`)
- `choices` are shuffled in `explainer.py`; `quiz.py` shuffles question order but not choices
- Ctrl+C during quiz discards all output (no partial CSV written)

### File Formats

- `_source.txt`: UTF-8 no BOM, CRLF, plain English text only
- `_wordlist.json`: `[{word, pos, sentence}]` — lemma, spaCy pos tag, single sentence from subtitle
- `_quiz.json`: `[{word, sentence, correct, choices[4]}]` — `correct` is one of the 4 `choices`
- `_quiz_result.csv`: UTF-8 no BOM, LF, columns: `word,pos,correct,sentence` (incorrect answers only)
- `_wordlist.md`: All words grouped ADJ → ADV → VERB, alphabetical within each section

### コーディングルール  

- 型ヒントをつける  
- docstringを書く  