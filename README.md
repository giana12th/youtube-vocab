# youtube-vocab

YouTube動画の英語字幕から単語を抽出し、ターミナルで4択クイズを出題するツール。

## 使い方

```bash
# YouTube URLを渡すだけ
uv run main.py https://youtube.com/watch?v=VIDEO_ID

# テキストファイルでも可
uv run main.py my_article.txt
```

字幕取得 → 単語抽出 → Claude による選択肢生成 → クイズ の順に自動で進む。

## セットアップ

```bash
# 依存関係のインストール
uv sync

# spaCy 英語モデルのダウンロード（初回のみ）
uv run -m spacy download en_core_web_sm
```

`claude` コマンド（Claude Code）がインストールされている必要がある。

## 出力

クイズ終了後、`output/` に2ファイルが生成される。

| ファイル | 内容 |
|---|---|
| `{date}_{id}_quiz_result.csv` | 不正解だった単語（再利用用） |
| `{date}_{id}_wordlist.md` | 全単語リスト（参照用） |

## ステップ単体実行

途中からやり直したい場合は各スクリプトを直接実行できる。

```bash
uv run extractor.py   # 単語抽出をやり直す
uv run explainer.py   # 選択肢生成をやり直す（Claude再呼び出し）
uv run quiz.py        # クイズだけもう一度
```

引数なしで実行すると `output/` 内の最新セッションを自動検出する。
