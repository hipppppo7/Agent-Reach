# メンテナンス

更新が失敗したとき、ブラウザが起動しないとき、チャネルがエラーを出すとき、またはユーザーがアンインストールを求めたときに読む。

- 更新：`agent-reach update` は Agent Reach、追加済みチャネルのツール、skill をアップグレードする。`agent-reach update --check` は新しいバージョンがあるかだけを確認する。ユーザーの同意を得てからのみ実行する。
- 状態：`agent-reach doctor --text` はローカルの状態を読むだけでネットワークに接続しない。`agent-reach check <channel> --text` はネットワークに接続して1回実地テストする（`--search` は検索／求人だけをテストする）。インストール成功は実地テスト合格と同じではない。
- ブラウザ：`agent-reach browser status` で状態を確認、`browser setup` でエンジンと拡張機能を準備、`browser stop` で閉じる。CloakBrowser のダウンロードに失敗した場合は、ネットワークを直してから `browser setup --retry-cloak` を実行できる。
- 失敗した段階を区別する：依存関係のダウンロード、ブラウザ接続、ログイン、ページの読み込み、プラットフォームのレート制限はそれぞれ別物。ネットワークのタイムアウトをログイン失効と言わない。
- 上流ツールのエラー：エラー内容とバージョンを記録し、ユーザーの同意を得てから `agent-reach update` を1回実行する。上流ツールのインストール済みファイルを書き換えない。リトライを繰り返さない。
- `PLATFORM_BLOCKED`、`RATE_LIMITED`、`NEED_LOGIN`、`BUSY` が出たら今回の試行をやめ、ユーザーが対処してから続行する。ウィンドウを繰り返し開かない。
- キーとプロキシ：`agent-reach configure groq-key | openai-key | proxy | github-token`。値はユーザー本人が提供する。
- アンインストール：まず `agent-reach uninstall --dry-run` で範囲をユーザーに見せ、確認を得てから `agent-reach uninstall`。削除するのは Reach 自身がインストールしたものだけで、ユーザーのその他のファイルとブラウザは残す。
