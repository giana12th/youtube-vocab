# 中間ファイル仕様：`{date}_{id}_source.txt`

## 役割

- 入力源（YouTube字幕・任意テキスト）から取得した英文を保存する中間ファイル
- `extractor.py` はこのファイルのみを読めばよい（入力源を知らない）
- 手動で作成・編集して渡すことも可能

---

## ファイル名規則

```
{date}_{id}_source.txt
```

| 入力源 | `id` 部分の決め方 |
|---|---|
| YouTube URL | YouTube動画ID（例: `VIDEO_ID`） |
| テキストファイル | ファイル名から拡張子を除いたもの（例: `my_article`） |

例：
```
output/20240315_VIDEO_ID_source.txt
output/20240315_my_article_source.txt
```

idは最大20文字まで。オーバーする場合は先頭から20文字を使用する。  

---

## フォーマット仕様

| 項目 | 仕様 |
|---|---|
| 文字コード | UTF-8（BOMなし） |
| 改行コード | CRLF（`\r\n`） |
| 内容 | 英文のみ。メタデータ・タイムスタンプは含めない |
| 改行の扱い | **任意**。1文1行でも段落まとめでも可 |
| 空行 | 許容する（段落区切りとして使ってよい） |
| エンコーディング外の文字 | 除去または `?` に置換して保存 |

> `extractor.py` は spaCy の文境界検出で文分割するため、改行スタイルに依存しない。

---

## サンプル

```
The results were quite ambiguous at first.
She meticulously reviewed every document before signing.

We need to scrutinize these findings carefully.
The committee was reluctant to endorse the proposal without further evidence.
```

---

## 設計判断の記録

| 判断 | 理由 |
|---|---|
| 中間ファイルをプレーンテキストにした | JSON等より人間が読みやすく、手動編集も容易 |
| 改行を自由にした | YouTube字幕・任意テキストで改行単位が異なるため強制しない |
| メタデータをテキストに含めない | 入力源ごとに構造が異なると解析が複雑になるため分離 |
| テキストファイルはそのまま渡す設計にした | `plaintext.py` のような中継モジュールは不要な間接層になる |
| `_source.txt` を output/ に保存する | デバッグ・再実行時に入力取得をスキップできる |