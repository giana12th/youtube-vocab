# 実装計画：YouTube英語字幕 単語学習システム

作成日：2026-02-28

---

## 1. 前提確認

### 設計書の完成状況

| ドキュメント | 状態 | 備考 |
|---|---|---|
| `youtube_vocab_plan.md` | ✅ 完成 | 全体方針・スコープ確定 |
| `workflow_design.md` | ✅ 完成 | ファイル構成・処理フロー・エラー方針確定 |
| `source_format_spec.md` | ✅ 完成 | `_source.txt` のフォーマット確定 |
| `json_format_spec.md` | ✅ 完成 | `_wordlist.json` / `_quiz.json` のスキーマ確定 |
| `output_format_spec.md` | ✅ 完成 | `_quiz_result.csv` / `_wordlist.md` のフォーマット確定 |
| `prompt_design.md` | ✅ 完成 | `explainer.py` → `claude -p` のプロンプト設計確定 |

設計書はすべて揃っており、実装に進める状態。

---

## 2. 実装対象ファイルと責務

```
youtube-vocab/
├── main.py          # エントリーポイント・ステップ呼び出し・入力種別の分岐
├── subtitle.py      # YouTube URL → output/{session_id}_source.txt
├── source.py        # テキストファイル → output/{session_id}_source.txt
├── extractor.py     # _source.txt → _wordlist.json
├── config.py        # zipfのしきい値設定
├── explainer.py     # _wordlist.json → _prompt.md → _quiz.json（claude -p 呼び出し）
├── quiz.py          # _quiz.json → クイズ実行 → _quiz_result.csv + _wordlist.md
├── pyproject.toml   # uv プロジェクト設定・依存関係
└── output/          # 中間ファイル・出力ファイル置き場（.gitignore 対象）
```

---

## 3. 依存ライブラリ

インストール済み  

| ライブラリ | 用途 | バージョン方針 |
|---|---|---|
| `youtube-transcript-api` | YouTube字幕取得 | 最新安定版 |
| `spacy` | 品詞判定・文境界検出・lemma抽出 | `en_core_web_sm` モデル使用 |
| `wordfreq` | 単語頻度スコア（zipf）によるフィルタ | 最新安定版 |

外部コマンド依存：
- `claude` コマンド（Claude Code）：`explainer.py` が `subprocess.run(["claude", "-p"])` で呼び出す

---

## 4. 実装ステップ（推奨順序）

疎結合設計のため、各ステップは独立して動作確認が可能。

### Step 1：プロジェクト初期化 完了

- `uv init` でプロジェクト作成
- `pyproject.toml` に依存関係を記載
- `output/` ディレクトリを作成、`.gitignore` に追加
- spaCy の英語モデルをダウンロード：`uv run -m spacy download en_core_web_sm`

### Step 2：`subtitle.py`

**入力：** YouTube URL（コマンドライン引数）
**出力：** `output/{session_id}_source.txt`

実装内容：
- `youtube-transcript-api` で字幕取得
- 複数トラックがある場合：手動字幕 > 自動生成字幕、言語は `en` 優先
- タイムスタンプを除去してテキストのみ抽出
- CRLF、UTF-8（BOMなし）で保存
- `_source.txt` が既存の場合はスキップしてセッションIDのみ返す

エラーケース：
- 字幕が存在しない → `[ERROR] subtitle.py: 字幕が見つかりません`
- YouTube以外のURLが来た場合は `main.py` 側でガード済み

### Step 3：`source.py`

**入力：** テキストファイルパス（コマンドライン引数）
**出力：** `output/{session_id}_source.txt`

実装内容：
- ファイルを読み込み、UTF-8で `_source.txt` に書き出す（実質コピー＋名前変換）
- UTF-8以外の文字は `?` に置換
- `_source.txt` が既存の場合はスキップ

### Step 4：`extractor.py`

**入力：** `output/{session_id}_source.txt`
**出力：** `output/{session_id}_wordlist.json`

実装内容：
1. `_source.txt` を読み込む
2. spaCy で文境界検出・品詞判定・lemma抽出
3. 対象品詞：`ADJ` / `ADV` / `VERB` のみ
4. wordfreq の `zipf_frequency(word, 'en')` でスコアを取得
5. zipf ≥ 4.0 の高頻出語を除外（上位約3,000〜5,000語相当）
6. 同一単語の重複排除（最初の出現文を採用）
7. 20件超の場合は絞り込みルールを適用：
   - 品詞優先順位：ADJ > ADV > VERB
   - 同品詞内はzipfスコア昇順（低い＝希少）
   - 同スコアは出現順
8. `_wordlist.json` に出力（最大20件）

注意点：
- spaCy の pos タグは `token.pos_` で取得（`"ADJ"` / `"ADV"` / `"VERB"` と一致）
- lemma は `token.lemma_` で取得、小文字化

### Step 5：`explainer.py`

**入力：** `output/{session_id}_wordlist.json`
**出力：** `output/{session_id}_prompt.md`、`output/{session_id}_quiz.json`

実装内容：
1. `_wordlist.json` を読み込む
2. `prompt_design.md` に定義された Instructions テンプレートに wordlist の JSON を埋め込む
3. `_prompt.md` として書き出す（デバッグ用）
4. `subprocess.run(["claude", "-p"], input=prompt_text, ...)` で Claude を呼び出す
5. stdout を `parse_claude_output()` でパース（3段階フォールバック）
6. バリデーション実施（配列長・キー存在・distractors長・correct重複）
7. `wordlist.json` の `sentence` を結合
8. `correct + distractors` の4要素をシャッフルして `choices` を生成
9. `_quiz.json` に出力

エラーハンドリング（`prompt_design.md` 準拠）：
- `claude` コマンドが見つからない → エラー終了
- JSONパース失敗 → `_claude_raw.txt` に保存してエラー終了
- 有効エントリが50%未満 → エラー終了（再実行を促す）

### Step 6：`quiz.py`

**入力：** `output/{session_id}_quiz.json`
**出力：** `output/{session_id}_quiz_result.csv`、`output/{session_id}_wordlist.md`

実装内容：
1. `_quiz.json` を読み込む
2. 問題順をシャッフル
3. ターミナルに問題を表示（`youtube_vocab_plan.md` のUIデザイン準拠）
4. 入力受付：`1`〜`4` のみ受け付け、それ以外は再表示
5. 正誤フィードバックを表示
6. Ctrl+C 中断時：ファイル出力なしで終了
7. 全問終了後：
   - `_quiz_result.csv`：不正解単語のみ（`output_format_spec.md` 準拠）
   - `_wordlist.md`：全単語を品詞ごとにアルファベット順（`output_format_spec.md` 準拠）

CSV仕様（`output_format_spec.md` 準拠）：
- UTF-8、BOMなし、LF
- カラム：`word,pos,correct,sentence`
- 不正解0件はヘッダー行のみ出力

wordlist.md 仕様（`output_format_spec.md` 準拠）：
- セクション順：ADJ → ADV → VERB（空セクションは省略）
- 品詞内はアルファベット順

### Step 7：`main.py`

**入力：** コマンドライン引数（URL or ファイルパス）
**出力：** なし（各モジュールに委譲）

実装内容：
- 引数の種別判定（URL / ファイルパス）
- `subtitle.py` または `source.py` をモジュールとして `import` し `run(url_or_path)` を呼ぶ
- 以降 `extractor.run(session_id)` → `explainer.run(session_id)` → `quiz.run(session_id)` を順に呼ぶ
- 各ステップがエラーで終了した場合はそこで停止

各モジュールのインターフェース（共通）：
```python
def run(session_id: str) -> None:
    ...
```
`subtitle.py` / `source.py` のみ：
```python
def run(url_or_path: str) -> str:  # session_id を返す
    ...
```

---

## 5. セッションID生成ロジック

```python
from datetime import date

def make_session_id(video_id_or_filename: str) -> str:
    today = date.today().strftime("%Y%m%d")
    return f"{today}_{video_id_or_filename}"
```

- YouTube URL → `urllib.parse` で `v=` パラメータを抽出
- テキストファイル → `Path(filepath).stem` でベース名を取得

---

## 6. 単体実行時のセッション自動検出ロジック

`extractor.py` / `explainer.py` / `quiz.py` を引数なしで実行した場合：

```python
import os
from pathlib import Path

def detect_latest_session() -> str:
    output_dir = Path("output")
    # _source.txt のファイル名から日付部分を取得
    files = list(output_dir.glob("*_source.txt"))
    if not files:
        raise FileNotFoundError("output/ にセッションが見つかりません")
    # ファイル名の日付（YYYYMMDD）でソート、同日はmtimeで比較
    files.sort(key=lambda f: (f.name[:8], f.stat().st_mtime), reverse=True)
    # {date}_{id}_source.txt → {date}_{id} を返す
    return files[0].name.replace("_source.txt", "")
```

---

## 7. 実装上の注意点・設計書から読み取れる制約

| 項目 | 内容 |
|---|---|
| `pos` の値 | spaCy の `token.pos_` が返す文字列（`"ADJ"` / `"ADV"` / `"VERB"`）をそのまま使う |
| `sentence` の取得 | spaCy の `token.sent` で文を取得。前後の文は含めない |
| zipf スコアのしきい値 | `zipf_frequency(word, 'en') >= 4.0` を除外（`json_format_spec.md`） |
| Ctrl+C の扱い | `try/except KeyboardInterrupt` で捕捉し、ファイル出力せず終了 |
| `choices` のシャッフル | `explainer.py` 生成時に実施済み。`quiz.py` では再シャッフルしない |
| クイズ問題順 | `quiz.py` がロード時にシャッフル（`quiz.json` の順序に依存しない） |
| `_source.txt` スキップ | ステップ1のみ。ステップ2以降は常に再生成 |
| 字幕取得言語優先 | 手動字幕 > 自動生成字幕、言語は `en` 優先 |

---

## 8. 実装順序の推奨理由

```
Step 1（初期化）
→ Step 2/3（入力取得：どちらか片方だけ先に作ってもよい）
→ Step 4（extractor：spaCy/wordfreq の動作確認が先決）
→ Step 5（explainer：Claude連携の動作確認）
→ Step 6（quiz：出力フォーマットの確認）
→ Step 7（main：全体を繋げる）
```

`extractor.py` → `explainer.py` の境界でデータ検証を挟むと、Claude呼び出し前に問題を発見できて効率的。

---

## 9. テスト方針

単体テストは作らない（シンプルさ優先）。  
各ステップを手動で単体実行して動作確認する。

```bash
# 字幕取得の確認
uv run subtitle.py https://youtube.com/watch?v=VIDEO_ID

# 単語抽出の確認（output/に_source.txtがある状態で）
uv run extractor.py

# Claude連携の確認
uv run explainer.py

# クイズの確認
uv run quiz.py
```
