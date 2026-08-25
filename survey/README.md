# 子どものAIとみんなの声（アンケート可視化ページ）

子どものAI利用に関する保護者アンケートの回答を集計・可視化する公開ページです。
親御さんに「3分のご協力」を呼びかけ、集まった声をグラフで見せます。

- 公開URL（予定）: https://sy-08.github.io/children/survey/
- データ元: Google フォーム回答スプレッドシート
- 運用: すべて GitHub Pages + GitHub Actions で完結（追加費用なし）

## 構成

| ファイル | 役割 |
|---|---|
| `survey/index.html` | 可視化ページ本体（単一HTML）。`data.json` を読み込んで描画。取得できない環境では埋め込みデータで表示。 |
| `survey/data.json` | 集計結果の初期値（シード）。実際の公開ページは毎回ビルドし直した最新データで配信される。 |
| `scripts/build_survey.py` | スプレッドシートをCSVで取得し集計、`data.json` を出力。 |
| `.github/workflows/update-survey.yml` | 毎日 06:00(JST) に集計→そのまま Pages に再デプロイ（自己完結）。手動実行も可。 |

## 更新のしくみ

1. GitHub Actions（`update-survey.yml`）が1日1回（06:00 JST）起動。
2. `build_survey.py` がスプレッドシートを `export?format=csv` で取得（リンク共有ONのため認証不要）。
3. 動作確認用のテスト回答（Q1または自由記述に「テスト」を含む行）を除外して集計し `survey/data.json` を生成。
4. 既存の `pages.yml` と同じ方式で、その場でサイト全体を GitHub Pages に再デプロイ。公開ページは常に最新。

※ 既存の `pages.yml`（push時にサイト全体を配信）はそのまま。日次ジョブは同じ `concurrency: pages` グループで同時実行を避けています。

## 手動で更新したいとき

GitHub リポジトリの **Actions → Update survey data → Run workflow** を押すと即時更新できます。

## メモ

- アンケート回答フォームのURLは `index.html` 内の `SURVEY_FORM_URL` に設定します。
- 個人が特定される情報（氏名・メール等）は収集・掲載していません。
