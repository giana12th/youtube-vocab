# 中間ファイル JSONフォーマット仕様

## ファイル一覧

| ファイル名 | 生成タイミング | 生成元 | 用途 |
|---|---|---|---|
| `{date}_{videoID}_wordlist.json` | 単語抽出後 | `extractor.py` | Claudeへの入力（最大20件） |
| `{date}_{videoID}_prompt.md` | Claude呼び出し前 | `explainer.py` | `claude -p` に渡すプロンプト |
| `{date}_{videoID}_quiz.json` | Claude処理後 | `explainer.py` | クイズ実行の入力 |

日付フォーマット：`YYYYMMDD`（例: `20240315_VIDEO_ID_wordlist.json`）

---

## 1. wordlist.json

### 概要

spaCyによる品詞判定・wordfreqフィルタ後の単語リスト。Claudeへそのまま渡す。

### スキーマ

```json
[
  {
    "word": "string",      // 原形（lemma）
    "pos": "string",       // 品詞タグ（spaCy準拠）
    "sentence": "string"   // 字幕から抜いた出現文
  }
]
```

### フィールド詳細

| フィールド | 型 | 説明 |
|---|---|---|
| `word` | string | spaCyのlemma（原形）。小文字。 |
| `pos` | string | `ADJ` / `ADV` / `VERB` のいずれか |
| `sentence` | string | 字幕から抜いた1文。前後の文は含めない。 |

### 制約

- wordfreqのzipfスコアによるバンドパスフィルタ適用済み（2.0 <= zipf < 5.0）
- zipf < 2.0（未登録語・ミーム等）およびzipf >= 5.0（基礎的すぎる語）は除外
- 同一単語の重複は除外（最初の出現文を採用）
- フィルタ後の候補が20件未満の場合はその件数をそのまま出力する
- 20件を超える場合は絞り込みルールに従い上位20件を出力する（`extractor.py` が責任を持つ）
- zipfのしきい値は設定で変えられるようにする  

### 20件への絞り込みルール

候補が20件を超えた場合、以下の優先順位で上位20件を選択する。

**第1優先：品詞**

| 順位 | 品詞 |
|---|---|
| 1 | ADJ（形容詞） |
| 2 | ADV（副詞） |
| 3 | VERB（動詞） |

**第2優先：zipfスコア（同一品詞内の並び順）**

zipfスコアが高い語を優先する（スコアが高い＝より一般的＝学習価値が高い語）。
スコアが同じ場合は字幕内の出現順（先に出た語を優先）。

**適用例**

候補が ADJ×10, ADV×8, VERB×15 の33件あった場合：
- ADJ 10件をすべて採用
- ADV 8件をすべて採用
- VERB は残り2枠のみ → zipfスコアが高い順に上位2件を採用

### サンプル

```json
[
  {
    "word": "ambiguous",
    "pos": "ADJ",
    "sentence": "The results were quite ambiguous at first."
  },
  {
    "word": "meticulously",
    "pos": "ADV",
    "sentence": "She meticulously reviewed every document."
  },
  {
    "word": "scrutinize",
    "pos": "VERB",
    "sentence": "We need to scrutinize these findings carefully."
  }
]
```

---

## 2. quiz.json

### 概要

Claudeが生成した選択肢を加工・保存したファイル。クイズ実行時に読み込む。

### スキーマ

```json
[
  {
    "word": "string",       // 出題する英単語（原形）
    "sentence": "string",   // 例文（wordlistから引き継ぐ）
    "correct": "string",    // 正解の日本語訳
    "choices": ["string"]   // 4択の選択肢（シャッフル済み）
  }
]
```

### フィールド詳細

| フィールド | 型 | 説明 |
|---|---|---|
| `word` | string | wordlist.json の `word` をそのまま引き継ぐ |
| `sentence` | string | wordlist.json の `sentence` をそのまま引き継ぐ |
| `correct` | string | `choices` 内の文字列と完全一致する必要がある |
| `choices` | string[] | 正解1つ + 誤答3つ。`explainer.py` でシャッフル済み |

### 制約

- `choices` は必ず4要素
- `correct` は `choices` のいずれか1つと完全一致すること
- `choices` の順序は `explainer.py` 生成時にシャッフルする（実行時の再シャッフルは不要）

### サンプル

```json
[
  {
    "word": "ambiguous",
    "sentence": "The results were quite ambiguous at first.",
    "correct": "曖昧な",
    "choices": ["明確な", "曖昧な", "否定的な", "重要な"]
  },
  {
    "word": "meticulously",
    "sentence": "She meticulously reviewed every document.",
    "correct": "細心の注意を払って",
    "choices": ["大雑把に", "細心の注意を払って", "素早く", "繰り返し"]
  }
]
```

---

## Claudeからのレスポンス形式（explainer.py内部処理用）

Claudeには以下の形式でJSONのみを返すよう指示する。`explainer.py` はこれを受け取って `choices` を組み立て、`quiz.json` に変換する。

```json
[
  {
    "word": "ambiguous",
    "correct": "曖昧な",
    "distractors": ["明確な", "否定的な", "重要な"]
  }
]
```

### wordlist.json → quiz.json 変換ルール

1. Claudeレスポンスの `word` をキーに `wordlist.json` の `sentence` を結合
2. `correct` + `distractors` を合わせた4要素をシャッフルして `choices` を生成
3. `correct` はそのまま保持

---

## ディレクトリ構成

```
output/
├── 20240315_VIDEO_ID_wordlist.json    # 単語抽出結果（最大20件）
├── 20240315_VIDEO_ID_prompt.md        # claude -p に渡したプロンプト
├── 20240315_VIDEO_ID_quiz.json        # クイズデータ
├── 20240315_VIDEO_ID_quiz_result.csv  # 不正解単語
└── 20240315_VIDEO_ID_wordlist.md      # 全単語リスト（参照用）
```