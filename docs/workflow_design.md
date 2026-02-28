# ワークフロー設計

## 実行環境

Python の実行は `uv run` を使う。

```bash
uv run main.py https://youtube.com/watch?v=ZY34OTV30Ck
uv run extractor.py
```

---

## ファイル構成

```
youtube-vocab/
├── main.py        # エントリーポイント・ステップ呼び出し・入力種別の分岐
├── subtitle.py    # YouTube URL → _source.txt
├── source.py      # テキストファイル → _source.txt
├── extractor.py   # _source.txt → _wordlist.json
├── config.py      # zipfのしきい値設定
├── explainer.py   # _wordlist.json → _quiz.json（claude -p 呼び出し）
├── quiz.py        # _quiz.json → クイズ実行 → _result.csv + _wordlist.md
└── output/        # 中間ファイル・出力ファイル置き場
```

---

## ステップ概要

| ステップ | スクリプト | 入力 | 出力 |
|---|---|---|---|
| 1a | `subtitle.py` | YouTube URL | `_source.txt` |
| 1b | `source.py` | テキストファイル | `_source.txt` |
| 2 | `extractor.py` | `_source.txt` | `_wordlist.json` |
| 3 | `explainer.py` | `_wordlist.json` | `_quiz.json` |
| 4 | `quiz.py` | `_quiz.json` | `_result.csv` + `_wordlist.md` |

ステップ1a と 1b は排他。2〜4 は入力源に関わらず共通。

**既存ファイルのスキップ：**
ステップ1（`subtitle.py` / `source.py`）は、対象セッションの `_source.txt` がすでに `output/` に存在する場合はスキップして次ステップへ進む。ステップ2以降はスキップしない（再実行時は常に再生成する）。

---

## セッションID

URLまたはファイル名が確定した時点でセッションIDが決まる。以降の全ステップはこのIDで中間ファイルを解決する。

```
{YYYYMMDD}_{id}

例：
20260228_ZY34OTV30Ck   # YouTube動画ID
20260228_my_article    # テキストファイル名（拡張子除く）
```

中間ファイルはすべて `output/` に置く：

```
output/
├── 20260228_ZY34OTV30Ck_source.txt
├── 20260228_ZY34OTV30Ck_wordlist.json
├── 20260228_ZY34OTV30Ck_quiz.json
├── 20260228_ZY34OTV30Ck_quiz_result.csv
└── 20260228_ZY34OTV30Ck_wordlist.md
```

---

## 実行方法

### 一気貫通（通常の使い方）

```bash
# YouTube URL
uv run main.py https://youtube.com/watch?v=ZY34OTV30Ck

# テキストファイル
uv run main.py my_article.txt
```

### ステップ単体実行

引数省略時は `output/` 内の最新セッションを自動検出する。
セッションIDを指定すれば特定のセッションを対象にできる。

**最新セッションの自動検出ロジック：**
`output/` 内のファイル名に含まれる日付部分（`YYYYMMDD`）を比較し、最も新しい日付のセッションを取得する。
同一日付に複数セッションが存在する場合は、ファイルの更新日時が最新のものを選択する。

```bash
# ステップ1：入力源に応じて使い分け
uv run subtitle.py https://youtube.com/watch?v=ZY34OTV30Ck
uv run source.py my_article.txt

# ステップ2以降：引数省略で最新セッションを自動検出
uv run extractor.py
uv run explainer.py
uv run quiz.py

# セッション指定（特定セッションを再実行したい場合）
uv run explainer.py 20260228_ZY34OTV30Ck
uv run quiz.py 20260228_ZY34OTV30Ck
```

### 途中からの再実行

疎結合設計により、任意のステップから再開できる。
例：`explainer.py` の出力が気に入らない場合：

```bash
uv run explainer.py   # _quiz.json を再生成
uv run quiz.py        # そのままクイズ実行
```

---

## main.py の処理フロー

```
引数を受け取る
↓
http:// または https:// で始まる
  → youtube.com または youtu.be を含む → subtitle.py を呼ぶ
  → それ以外 → エラー終了
それ以外（ファイルパス）
  → ファイルが存在しない → エラー終了
  → ファイルが存在する  → source.py を呼ぶ
↓
extractor.py を呼ぶ
↓
explainer.py を呼ぶ
↓
quiz.py を呼ぶ
```

各ステップはサブプロセスではなく、モジュールとして import して `run(session_id)` を呼ぶ。

---

## explainer.py の処理フロー

```
_wordlist.json を読み込む
↓
プロンプトを組み立てる（単語リストをJSONで埋め込む）
↓
subprocess.run(["claude", "-p", prompt]) を実行
↓
stdout を受け取り JSON としてパース
↓
wordlist.json の sentence と結合
↓
choices（correct + distractors）をシャッフル
↓
_quiz.json を書き出す
```

Claude Code は `claude -p` のワンショットモードで呼び出す。
プロンプトの詳細設計は別途 `prompt_design.md` で行う。

---

## エラー処理方針

- 各ステップでエラーが発生した場合、メッセージを出力して処理を終了する
- リトライは行わない
- 中間ファイルが存在する場合は途中から再実行できるため、再実行で対応する
- クイズ実行中（`quiz.py`）に Ctrl+C で中断した場合、それまでの不正解データは破棄する。出力ファイルは生成しない。
- 字幕取得（`subtitle.py`）で字幕が存在しない場合はエラー終了する。複数の字幕トラックが存在する場合は手動字幕を優先し、手動字幕がなければ自動生成字幕を使用する。言語は `en` を優先する。

```
[ERROR] extractor.py: source.txt が見つかりません: output/20260228_ZY34OTV30Ck_source.txt
[ERROR] explainer.py: claude コマンドが見つかりません。Claude Code がインストールされているか確認してください。
[ERROR] explainer.py: Claude のレスポンスを JSON としてパースできませんでした。
```

---

## クイズ UI 仕様（quiz.py）

- **出題順序**：`quiz.json` の順序をシャッフルして出題する
- **回答入力**：`1`〜`4` の数字キー入力。それ以外の入力は無視して同じ問題を再表示する
- **中断**：Ctrl+C で強制終了。不正解データは破棄し、出力ファイルは生成しない
- **正誤フィードバック**：回答後に正解・不正解を表示してから次の問題へ進む
