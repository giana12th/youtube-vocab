# 出力ファイル フォーマット仕様

## 対象ファイル

| ファイル名 | 用途 |
|---|---|
| `{date}_{videoID}_quiz_result.csv` | 不正解単語の記録・再利用 |
| `{date}_{videoID}_wordlist.md` | クイズ後の参照用単語リスト |

日付フォーマット：`YYYYMMDD`（例: `20240315_VIDEO_ID_quiz_result.csv`）

---

## 1. quiz_result.csv

### 概要

クイズで**不正解だった単語のみ**を記録するCSV。自作ツールでの再利用を前提とし、フォーマットを明確に固定する。

### スキーマ

```
word,pos,correct,sentence
```

| カラム名 | 型 | 説明 | 例 |
|---|---|---|---|
| `word` | string | 英単語（原形・小文字） | `ambiguous` |
| `pos` | string | 品詞タグ（`ADJ` / `ADV` / `VERB`） | `ADJ` |
| `correct` | string | 正解の日本語訳 | `曖昧な` |
| `sentence` | string | 字幕から抜いた例文（原文） | `The results were quite ambiguous at first.` |

### エンコーディング・フォーマット規則

- 文字コード：**UTF-8**（BOMなし）
- 改行コード：**LF**（`\n`）
- 区切り文字：**カンマ** `,`
- クォート：`sentence` など値にカンマ・ダブルクォートを含む場合は**RFC 4180準拠のダブルクォートエスケープ**を適用
- ヘッダー行：**あり**（1行目固定、順序固定）

### レコードの制約

- クイズで不正解だった単語のみ記録する（正解した単語は含めない）
- 同一セッション内で同じ単語を複数回間違えても**1レコードのみ**出力
- 不正解が0件の場合は**ヘッダー行のみ**出力する（0バイトファイルにしない）

### サンプル

```csv
word,pos,correct,sentence
ambiguous,ADJ,曖昧な,The results were quite ambiguous at first.
scrutinize,VERB,細かく調べる,We need to scrutinize these findings carefully.
```

### カラム設計の意図

| カラム | なぜ含めるか |
|---|---|
| `word` | 再利用ツールでの主キー。フラッシュカードや検索の基準になる |
| `pos` | 品詞ごとのフィルタリング・集計に使う（形容詞だけ復習するなど） |
| `correct` | 正解訳をそのまま使える。ツール側で翻訳APIを叩く必要がない |
| `sentence` | 文脈ごと持ち運べる。例文として表示・音声化が可能 |

---

## 2. wordlist.md

### 概要

クイズ後に見返す**参照用**の単語リスト。読み取り専用。全単語（正誤問わず）を品詞ごとに整理して掲載する。

### ファイル構成

~~~markdown
# 単語リスト：{videoID}
{YYYY-MM-DD} | {videoURL}

---

## ADJ（形容詞）

### ambiguous
- **意味**：曖昧な
- **例文**：The results were quite ambiguous at first.

---

## ADV（副詞）

### meticulously
- **意味**：細心の注意を払って
- **例文**：She meticulously reviewed every document.

---

## VERB（動詞）

### scrutinize
- **意味**：細かく調べる
- **例文**：We need to scrutinize these findings carefully.
~~~

### 仕様詳細

| 要素 | 仕様 |
|---|---|
| 文字コード | UTF-8（BOMなし） |
| ヘッダー | `# 単語リスト：{videoID}`、次行に日付とURL |
| セクション順 | `## ADJ` → `## ADV` → `## VERB`（固定順） |
| セクションが空の場合 | 見出しごと省略する（空セクションを残さない） |
| 各単語エントリ | `### {word}` の下に `意味` と `例文` の2行 |
| 単語の並び順 | 品詞内はアルファベット順（昇順） |
| 掲載範囲 | クイズの正誤に関わらず**全単語**を掲載 |
| 不正解マーク | **付けない**（シンプルさを優先） |