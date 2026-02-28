# プロンプト設計：`explainer.py` → `claude -p`

## 前提

- 呼び出し方式：`claude -p` のワンショット（non-interactive）
- スキルは読み込まれないため、プロンプト内に指示を完結させる
- プロンプトと wordlist.json は**別ファイル**として独立して管理する
- wordlist.json は `extractor.py` 時点で最大20件に絞り込み済み（バッチ分割不要）

---

## ファイル構成

```
output/
├── {session_id}_wordlist.json     # extractor.py が生成（最大20件）
├── {session_id}_prompt.md         # explainer.py が生成・claude -p に渡す
└── {session_id}_quiz.json         # explainer.py が生成
```

`_prompt.md` はデバッグ・再実行時の確認用として `output/` に残す。
プロンプト本文だけ手編集して再実行、という操作も可能。

---

## 呼び出しコマンド

```bash
claude -p < output/{session_id}_prompt.md
```

Pythonからは `subprocess.run` の `input=` でstdinに流す。シェル展開を使わないため、エスケープ問題・ARG_MAX上限のリスクがない。

```python
import subprocess

with open(f"output/{session_id}_prompt.md") as f:
    prompt_text = f.read()

result = subprocess.run(
    ["claude", "-p"],
    input=prompt_text,
    capture_output=True,
    text=True
)
```

---

## プロンプトファイル（`_prompt.md`）の構成

Instructions セクションと Word List セクションの2部構成。
`explainer.py` が指示本文テンプレートに `wordlist.json` の内容を埋め込んで生成する。

```
## Instructions

{指示本文}

## Word List

{wordlist.jsonの内容}
```

---

## Instructions セクション（固定テンプレート）

```markdown
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
- Keep it concise: aim for 2–6 characters

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
- One object per word, in the same order as the input
```

---

## Word List セクション

`wordlist.json` の内容をそのまま貼り付ける。

```markdown
## Word List

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

## `_prompt.md` 完成イメージ

```markdown
## Instructions

You are an English vocabulary assistant for Japanese learners.
...（指示本文）...

## Word List

[
  { "word": "ambiguous", "pos": "ADJ", "sentence": "The results were quite ambiguous at first." },
  { "word": "meticulously", "pos": "ADV", "sentence": "She meticulously reviewed every document." },
  { "word": "scrutinize", "pos": "VERB", "sentence": "We need to scrutinize these findings carefully." }
]
```

---

## 期待する出力サンプル

Claudeの stdout にJSONのみが返る：

```json
[
  {
    "word": "ambiguous",
    "correct": "曖昧な",
    "distractors": ["明確な", "否定的な", "重要な"]
  },
  {
    "word": "meticulously",
    "correct": "細心の注意を払って",
    "distractors": ["大雑把に", "素早く", "繰り返し"]
  },
  {
    "word": "scrutinize",
    "correct": "細かく調べる",
    "distractors": ["さっと目を通す", "無視する", "まとめる"]
  }
]
```

---

## `explainer.py` での処理フロー

```
output/{session_id}_wordlist.json を読み込む
↓
Instructions テンプレートに wordlist.json の内容を埋め込む
↓
output/{session_id}_prompt.md を書き出す
↓
prompt_text = open("output/{session_id}_prompt.md").read()
subprocess.run(["claude", "-p"], input=prompt_text, capture_output=True, text=True) を実行
↓
stdout を受け取り JSON としてパース（後述）
↓
wordlist.json の sentence と結合
↓
correct + distractors をシャッフルして choices を生成
↓
output/{session_id}_quiz.json を書き出す
```

---

## パース処理とエラーハンドリング

Claudeの出力にコードブロックや前置きテキストが混入した場合に備え、3段階フォールバックでパースする。

```python
import json, re

def parse_claude_output(raw: str) -> list:
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
```

パース失敗時のエラー出力：

```
[ERROR] explainer.py: Claudeのレスポンスを JSON としてパースできませんでした。
[ERROR] explainer.py: raw output を output/{session_id}_claude_raw.txt に保存しました。
```

---

## バリデーション

パース後に以下をチェックする。

| チェック項目 | 期待値 | 異常時の処理 |
|---|---|---|
| 配列の長さ | `wordlist.json` の件数と一致 | `[WARN]` を出力し、一致する `word` のみ使用 |
| 各オブジェクトのキー | `word`, `correct`, `distractors` が存在する | 該当エントリをスキップして `[WARN]` を出力 |
| `distractors` の長さ | 3要素 | 該当エントリをスキップして `[WARN]` を出力 |
| `correct` が `distractors` に含まれない | 重複なし | 該当エントリをスキップして `[WARN]` を出力 |

有効なエントリが全体の50%未満の場合：

```
[ERROR] explainer.py: 有効なエントリが少なすぎます（{n}/{total}件）。explainer.py を再実行してください。
```

---

## 設計上の判断記録

| 判断 | 理由 |
|---|---|
| プロンプトをstdinで渡す | `"$(cat ...)"` によるシェル展開はARG_MAX上限（約2MB）とエスケープ問題のリスクがある。`subprocess.run` の `input=` 経由でstdinに流す方式が安全 |
| プロンプトを `.md` ファイルで渡す | シェルのエスケープ問題を回避。デバッグ時にプロンプト内容を直接確認・手編集できる |
| wordlist.json とプロンプトを別ファイルにする | プロンプト本文だけ変えて再実行、単語リストだけ変えて再実行、という操作が独立して行える |
| 指示を英語で書く | Claudeへの英語指示の方が応答精度が安定する。日本語訳の生成品質は指示言語に依存しない |
| `pos` を誤答生成に活用する | 品詞を揃えることで誤答の文法的整合性が上がり、クイズとして機能しやすくなる（形容詞問題の誤答が動詞にならない） |
| バッチ分割なし（20件上限を上流で保証） | extractor.py 側で20件に絞るため、explainer.py はバッチ管理を持たなくてよい |
| `_prompt.md` を output/ に残す | プロンプト変更の履歴として機能し、再実行時に「どのプロンプトで生成したか」を追跡できる |