"""Read-only session discovery and explicit connection choices. Never logs a user in."""
import json
import urllib.request
from datetime import datetime
from urllib.parse import urlsplit

from agent_reach.utils.lang import current_lang
from agent_reach.utils.url import host_matches

from .result import BAD_INPUT, ReachError

# Every user- or agent-facing string below exists in zh (upstream), en and ja.
# `current_lang()` picks one; see agent_reach/utils/lang.py.

# These describe public routes an agent can try, not authenticated Reach readiness.
# A successful sample depends on the tool, network exit, content and platform response.
_PUBLIC_ACCESS = {
    'zh': {
        'web': '先用 Agent 已有网页搜索和读取；只为剩余缺口调用 Reach。',
        'github': '公开仓库、README、Issue/PR 及公开评论可先用网页或公开接口。',
        'youtube': '公开搜索、简介可先读；原生工具的部分样本可取评论、字幕和时间戳。',
        'bilibili': '公开搜索、简介、统计可先读；部分公开接口可取评论及回复关系。',
        'xiaoyuzhou': '播客转录需要 Groq Key；安装不要求登录。',
        'v2ex': '公开主题正文和部分回复可先读；完整性、分页需要单独核对。',
        'reddit': '公开搜索、正文和部分评论可先读；部分公开 JSON 样本可含评论及 parent_id。',
        'twitter': '公开搜索摘要、部分单帖全文可先尝试；公开嵌入不提供评论流。',
        'xiaohongshu': '公开发现页可能提供笔记 ID 和作者；不据此认定正文、评论可读。',
        'instagram': '公开搜索或主页信息可先尝试；HTML 可能只有应用外壳，Caption 和评论未获统一验证。',
        'facebook': '公开搜索摘要可先尝试；帖子正文和评论取决于页面与访问路径。',
        'linkedin': '公开职位可先搜索、读详情；2026-10-21 已取得免登录职位样本，不保证所有职位可读。',
        'boss': '公开职位索引和页面可先尝试；本轮未做匿名粒度验收。',
        'xueqiu': '公开股票行情和名称搜索可先尝试；社区内容另按所选路径判断。',
    },
    'en': {
        'web': "Use the agent's own web search and reading first; call Reach only for what is left.",
        'github': 'Public repos, READMEs, issues/PRs and public comments can be read through the web or public APIs first.',
        'youtube': 'Public search and descriptions can be read first; some native-tool samples include comments, subtitles and timestamps.',
        'bilibili': 'Public search, descriptions and stats can be read first; some public APIs return comments and reply threads.',
        'xiaoyuzhou': 'Podcast transcription needs a Groq key; installing needs no login.',
        'v2ex': 'Public topic bodies and some replies can be read first; completeness and pagination must be checked separately.',
        'reddit': 'Public search, post bodies and some comments can be read first; some public JSON samples include comments and parent_id.',
        'twitter': 'Public search snippets and the full text of some single posts can be tried first; public embeds give no comment stream.',
        'xiaohongshu': 'The public explore page may give note IDs and authors; that alone does not mean bodies or comments are readable.',
        'instagram': 'Public search or profile info can be tried first; the HTML may be only the app shell, and captions and comments are not uniformly verified.',
        'facebook': 'Public search snippets can be tried first; post bodies and comments depend on the page and the access path.',
        'linkedin': 'Public jobs can be searched and read first; no-login job samples were obtained on 2026-10-21, but not every job is guaranteed readable.',
        'boss': 'The public job index and pages can be tried first; what works without login was not acceptance-tested this round.',
        'xueqiu': 'Public stock quotes and name search can be tried first; community content depends on the chosen path.',
    },
    'ja': {
        'web': 'まず Agent 自身のウェブ検索・読み取りを使う。足りない分だけ Reach を呼ぶ。',
        'github': '公開リポジトリ・README・Issue/PR・公開コメントは、まずウェブか公開 API で読める。',
        'youtube': '公開の検索と概要欄はまず読める。ネイティブツールの一部のサンプルではコメント・字幕・タイムスタンプも取れる。',
        'bilibili': '公開の検索・概要欄・統計はまず読める。一部の公開 API ではコメントと返信の関係も取れる。',
        'xiaoyuzhou': 'ポッドキャストの文字起こしには Groq のキーが要る。インストールにログインは不要。',
        'v2ex': '公開トピックの本文と一部の返信はまず読める。全件そろっているか・ページ送りは別に確かめる。',
        'reddit': '公開の検索・本文・一部のコメントはまず読める。一部の公開 JSON のサンプルにはコメントと parent_id が含まれる。',
        'twitter': '公開の検索スニペットと、一部の単体投稿の全文はまず試せる。公開の埋め込みではコメント欄は取れない。',
        'xiaohongshu': '公開の発見ページからノート ID と投稿者が取れることがある。それだけで本文・コメントが読めるとは判断しない。',
        'instagram': '公開の検索やプロフィール情報はまず試せる。HTML がアプリの外枠だけのことがあり、キャプションとコメントは一律には検証されていない。',
        'facebook': '公開の検索スニペットはまず試せる。投稿の本文とコメントはページとアクセス経路しだい。',
        'linkedin': '公開の求人はまず検索・詳細の読み取りができる。2026-10-21 にログインなしの求人サンプルは取れたが、すべての求人が読めるとは限らない。',
        'boss': '公開の求人一覧とページはまず試せる。ログインなしでどこまで取れるかは今回は検収していない。',
        'xueqiu': '公開の株価と銘柄名の検索はまず試せる。コミュニティの内容は選んだ経路しだい。',
    },
}

_CAPABILITY_LIMITS = {
    'zh': {
        'youtube': ['read 返回元信息和简介；没有独立 comments 动作。',
                    '字幕依赖可用轨道；转录还需配置服务及额度，登录不保证有字幕。'],
        'bilibili': ['read 返回元信息和简介；没有独立 comments 动作。',
                     'subtitle 当前读取首P已有字幕；可能要求登录，不代表整套多P视频。'],
        'reddit': ['read 仅承诺其返回的帖子和评论；不保证完整评论树，不提供发评论动作。'],
        'twitter': ['thread 仅覆盖实际返回的回复；不保证完整评论流，不提供发帖动作。'],
        'xiaohongshu': ['只报告实际读取的正文、已加载评论和回复，不承诺完整导出。'],
        'instagram': ['search 搜索用户；没有任意帖子 read 或独立 comments 动作。'],
        'facebook': ['当前仅声明 search/profile，不承诺独立帖文读取或评论导出。'],
        'linkedin': ['当前仅声明职位搜索和 JD 读取，不承诺联系人或动态抓取。'],
        'boss': ['当前仅声明职位搜索和 JD 读取；登录不保证平台始终允许访问。'],
        'v2ex': ['回复是否完整须核对分页与实际返回数量。'],
    },
    'en': {
        'youtube': ['read returns metadata and the description; there is no separate comments action.',
                    'Subtitles depend on available tracks; transcription also needs a configured service and quota, and logging in does not guarantee subtitles.'],
        'bilibili': ['read returns metadata and the description; there is no separate comments action.',
                     'subtitle currently reads only the existing subtitles of part 1; it may require login and does not cover a whole multi-part video.'],
        'reddit': ['read only promises the posts and comments it returns; no complete comment tree is guaranteed, and there is no commenting action.'],
        'twitter': ['thread only covers the replies actually returned; no complete comment stream is guaranteed, and there is no posting action.'],
        'xiaohongshu': ['Only reports the body, loaded comments and replies actually read; no full export is promised.'],
        'instagram': ['search finds users; there is no read for arbitrary posts and no separate comments action.'],
        'facebook': ['Currently declares search/profile only; reading individual posts or exporting comments is not promised.'],
        'linkedin': ['Currently declares job search and JD reading only; contacts and feed scraping are not promised.'],
        'boss': ['Currently declares job search and JD reading only; logging in does not guarantee the platform always allows access.'],
        'v2ex': ['Whether replies are complete must be checked against pagination and the number actually returned.'],
    },
    'ja': {
        'youtube': ['read はメタ情報と概要欄を返す。コメント専用のアクションはない。',
                    '字幕は使える字幕トラックがあるときだけ。文字起こしにはサービスの設定と利用枠も要り、ログインしても字幕があるとは限らない。'],
        'bilibili': ['read はメタ情報と概要欄を返す。コメント専用のアクションはない。',
                     'subtitle は今のところ P1 の既存の字幕だけを読む。ログインを求められることがあり、複数 P の動画全体ではない。'],
        'reddit': ['read が約束するのは実際に返した投稿とコメントだけ。コメントツリーが全部そろうとは限らない。コメントを書くアクションはない。'],
        'twitter': ['thread は実際に返った返信だけ。コメント欄が全部そろうとは限らない。投稿するアクションはない。'],
        'xiaohongshu': ['実際に読んだ本文と、読み込まれたコメント・返信だけを報告する。全件の書き出しは約束しない。'],
        'instagram': ['search はユーザーを探す。任意の投稿の read とコメント専用のアクションはない。'],
        'facebook': ['今のところ search/profile だけ。個別の投稿の読み取りやコメントの書き出しは約束しない。'],
        'linkedin': ['今のところ求人検索と求人票の読み取りだけ。連絡先やフィードの取得は約束しない。'],
        'boss': ['今のところ求人検索と求人票の読み取りだけ。ログインしてもプラットフォームが常にアクセスを許すとは限らない。'],
        'v2ex': ['返信が全件そろっているかは、ページ送りと実際に返った件数で確かめる。'],
    },
}


# Public web options and authenticated Reach actions; detailed limits stay in capability_summary.
_QUICK_ACCESS = {
    'zh': {
        'xiaoyuzhou': ('🔑 转录需 Key', '—'),
        'github': ('✅ 找项目、读文档、看讨论、看评论', '—'),
        'youtube': ('✅ 找视频、读简介、读字幕', '—'),
        'bilibili': ('✅ 找视频、读简介', '❌ 读字幕'),
        'v2ex': ('✅ 读帖子、看回复', '—'),
        'web': ('✅ 搜资料、读网页', '—'),
        'reddit': ('✅ 搜帖子、读正文、看评论', '—'),
        'twitter': ('✅ 搜摘要、试读原文', '❌ 搜推文、看动态、看回复'),
        'xiaohongshu': ('✅ 搜摘要、找链接', '❌ 站内搜、读正文、看评论'),
        'instagram': ('✅ 搜简介', '❌ 找用户、看主页、看帖子'),
        'facebook': ('✅ 搜摘要', '❌ 站内搜、看主页'),
        'linkedin': ('✅ 找职位、读公开详情', '❌ 站内搜'),
        'boss': ('✅ 搜标题、找链接', '❌ 站内搜、读详情'),
        'xueqiu': ('✅ 找股票、查行情', '❌ 看热帖、看热股'),
    },
    'en': {
        'xiaoyuzhou': ('🔑 Transcription needs a key', '—'),
        'github': ('✅ Find projects, read docs, discussions and comments', '—'),
        'youtube': ('✅ Find videos, read descriptions and subtitles', '—'),
        'bilibili': ('✅ Find videos, read descriptions', '❌ Read subtitles'),
        'v2ex': ('✅ Read posts and replies', '—'),
        'web': ('✅ Search and read web pages', '—'),
        'reddit': ('✅ Search posts, read bodies and comments', '—'),
        'twitter': ('✅ Search snippets, try reading posts', '❌ Search tweets, timelines, replies'),
        'xiaohongshu': ('✅ Search snippets, find links', '❌ In-site search, read notes, comments'),
        'instagram': ('✅ Search bios', '❌ Find users, profiles, posts'),
        'facebook': ('✅ Search snippets', '❌ In-site search, profiles'),
        'linkedin': ('✅ Find jobs, read public details', '❌ In-site search'),
        'boss': ('✅ Search titles, find links', '❌ In-site search, read details'),
        'xueqiu': ('✅ Find stocks, check quotes', '❌ Hot posts, hot stocks'),
    },
    'ja': {
        'xiaoyuzhou': ('🔑 文字起こしにキーが必要', '—'),
        'github': ('✅ プロジェクト探し・ドキュメント・議論・コメント', '—'),
        'youtube': ('✅ 動画探し・概要欄・字幕', '—'),
        'bilibili': ('✅ 動画探し・概要欄', '❌ 字幕'),
        'v2ex': ('✅ 投稿・返信', '—'),
        'web': ('✅ 調べもの・ウェブページの読み取り', '—'),
        'reddit': ('✅ 投稿の検索・本文・コメント', '—'),
        'twitter': ('✅ 検索スニペット・投稿の読み取りを試す', '❌ ツイート検索・タイムライン・返信'),
        'xiaohongshu': ('✅ 検索スニペット・リンク探し', '❌ サイト内検索・本文・コメント'),
        'instagram': ('✅ プロフィール文の検索', '❌ ユーザー探し・プロフィール・投稿'),
        'facebook': ('✅ 検索スニペット', '❌ サイト内検索・プロフィール'),
        'linkedin': ('✅ 求人探し・公開の詳細', '❌ サイト内検索'),
        'boss': ('✅ タイトル検索・リンク探し', '❌ サイト内検索・詳細'),
        'xueqiu': ('✅ 銘柄探し・株価', '❌ 人気の投稿・人気の銘柄'),
    },
}

_DISPLAY_NAMES = {
    'zh': {
        'xiaoyuzhou': '小宇宙',
        'github': 'GitHub', 'youtube': 'YouTube', 'bilibili': 'B站', 'v2ex': 'V2EX',
        'web': '网页', 'reddit': 'Reddit', 'twitter': 'X / Twitter', 'facebook': 'Facebook',
        'instagram': 'Instagram', 'xiaohongshu': '小红书', 'linkedin': 'LinkedIn',
        'boss': 'BOSS直聘', 'xueqiu': '雪球',
    },
    'en': {
        'xiaoyuzhou': 'Xiaoyuzhou',
        'github': 'GitHub', 'youtube': 'YouTube', 'bilibili': 'Bilibili', 'v2ex': 'V2EX',
        'web': 'Web', 'reddit': 'Reddit', 'twitter': 'X / Twitter', 'facebook': 'Facebook',
        'instagram': 'Instagram', 'xiaohongshu': 'Xiaohongshu (RED)', 'linkedin': 'LinkedIn',
        'boss': 'BOSS Zhipin', 'xueqiu': 'Xueqiu',
    },
    'ja': {
        'xiaoyuzhou': '小宇宙（Xiaoyuzhou）',
        'github': 'GitHub', 'youtube': 'YouTube', 'bilibili': 'ビリビリ（Bilibili）', 'v2ex': 'V2EX',
        'web': 'ウェブ', 'reddit': 'Reddit', 'twitter': 'X / Twitter', 'facebook': 'Facebook',
        'instagram': 'Instagram', 'xiaohongshu': '小紅書（RED）', 'linkedin': 'LinkedIn',
        'boss': 'BOSS直聘', 'xueqiu': '雪球（Xueqiu）',
    },
}

_STATUS_LABELS = {
    'zh': {
        'not_added': '未接入，可按需添加', 'needs_setup': '待配置', 'unverified': '已接入，待实测',
        'ready': '已有有效验收', 'search_ready': '仅搜索已有验收',
        'needs_login': '所测动作要求登录', 'cooldown': '暂缓访问',
        'needs_user_action': '等待人工验证', 'broken': '当前路径故障',
    },
    'en': {
        'not_added': 'not added; add when needed', 'needs_setup': 'needs setup', 'unverified': 'added, not yet tested',
        'ready': 'verified', 'search_ready': 'only search verified',
        'needs_login': 'tested action needs login', 'cooldown': 'access paused',
        'needs_user_action': 'waiting for manual verification', 'broken': 'current path is broken',
    },
    'ja': {
        'not_added': '未追加（必要なら追加できる）', 'needs_setup': '設定待ち', 'unverified': '追加済み・実測前',
        'ready': '検収済み', 'search_ready': '検索だけ検収済み',
        'needs_login': '試したアクションにログインが必要', 'cooldown': 'アクセスを一時停止中',
        'needs_user_action': '手動の確認待ち', 'broken': '今の経路が故障中',
    },
}

# Short sentences for the receipt, the summary and the CLI.
_TEXT = {
    'zh': {
        'greet_morning': '早上好呀，想搜点什么？☀️', 'greet_noon': '中午好，想搜点什么？',
        'greet_afternoon': '下午好，想搜点什么？', 'greet_evening': '晚上好，想搜点什么？',
        'greet_night': '夜深了，想搜点什么？🌙',
        'upgrade_title': '**这次是从旧版本（1.5）升级上来的：**',
        'upgrade_kept': '- 你的密钥和设置都保留了。',
        'upgrade_web': '- RSS 订阅和 Exa 全网搜索不再单独提供，搜资料、读网页统一用"网页"。',
        'upgrade_browser': '- 推特、小红书这类要登录的平台，现在用 Agent Reach 自己的专用浏览器；第一次用时会先尝试复用你 Chrome 里的登录。',
        'upgrade_tools': '- 你以前另外装的命令行工具（比如 twitter-cli、bili）原样保留，没有删。',
        'upgrade_suggested': '- 你以前用过{names}，想继续用直接跟我说"加上 XX"。', 'list_sep': '、',
        'upgrade_removed': '- 旧版程序已经删掉，以后不会和新版冲突。',
        'upgrade_failed': '- 旧版程序没删成，请运行：`{command}`',
        'done': '安装完成', 'almost': '安装还差一步',
        'headline': '**Agent Reach {version} {state}。** 默认功能：{installed}/{total} 项准备成功。',
        'legend': '✅ 不用登录；❌ 登录后再试；🔑 需 Key；— 不用额外登录。',
        'table_head': '| 平台 | 不登录可以查什么 | 需要登录后再试 |',
        'install_failed': '（安装失败：{code}）', 'kept_removed': '（保留用户移除）', 'paren': '（{text}）',
        'verified': '已测通过：{names}。其余还没逐项联网测试。', 'verified_sep': '；', 'name_sep': '：',
        'not_verified': '还没逐项联网测试。',
        'sources': '摘要、标题和链接先从搜索引擎找；评论以已读内容为准，字幕需视频自带。',
        'ask': '**想查什么，直接说。** 会先尝试复用已有登录；确实需要你登录时，再打开窗口。',
        'public_default': '先尝试 Agent 已有公开搜索和读取。',
        'auth_note': '剩余任务的选定路径实际要求认证时，先复用已授权会话，再请用户登录；登录后仍需验证动作。',
        'summary_head': '先使用 Agent 已有公开搜索和读取；Reach 按需补充能力，安装不要求逐个平台登录。',
        'summary_line': '{channel}：{public} Reach {actions}（{status}）。{limits}',
        'evidence_note': '公开路径说明来自样本与访问条件，不能代替本机 Reach 验收；网络、403、超时或验证码均不能单独证明需要登录。',
        'setup_failed': '安装未完成：{code} {message}', 'report_saved': '完整报告已保存：{path}',
        'report_write_error': '安装报告未能保存；完整表格仍在 installation_report.markdown。',
        'reddit_login': '浏览器路径按需',
    },
    'en': {
        'greet_morning': 'Good morning! What shall we look up? ☀️', 'greet_noon': 'Hi! What shall we look up?',
        'greet_afternoon': 'Good afternoon! What shall we look up?', 'greet_evening': 'Good evening! What shall we look up?',
        'greet_night': "It's late. What shall we look up? 🌙",
        'upgrade_title': '**This was an upgrade from the old version (1.5):**',
        'upgrade_kept': '- Your keys and settings were kept.',
        'upgrade_web': '- RSS feeds and Exa web search are no longer separate; searching and reading pages now both go through "Web".',
        'upgrade_browser': "- Platforms that need a login, such as Twitter and Xiaohongshu, now use Agent Reach's own browser; the first time, it tries to reuse your logins from Chrome.",
        'upgrade_tools': '- Command-line tools you installed separately before (e.g. twitter-cli, bili) were left as they are, not deleted.',
        'upgrade_suggested': '- You used {names} before; to keep using them, just tell me "add XX".', 'list_sep': ', ',
        'upgrade_removed': '- The old program was removed, so it will not conflict with the new one.',
        'upgrade_failed': '- The old program could not be removed; please run: `{command}`',
        'done': 'is installed', 'almost': 'is one step short of installed',
        'headline': '**Agent Reach {version} {state}.** Default channels: {installed}/{total} ready.',
        'legend': '✅ no login needed; ❌ try after logging in; 🔑 needs a key; — no extra login.',
        'table_head': '| Platform | What works without login | Try after logging in |',
        'install_failed': ' (install failed: {code})', 'kept_removed': ' (left removed by you)', 'paren': ' ({text})',
        'verified': 'Tested OK: {names}. The rest have not been tested online one by one yet.', 'verified_sep': '; ', 'name_sep': ': ',
        'not_verified': 'Not yet tested online one by one.',
        'sources': 'Snippets, titles and links come from search engines first; comments are limited to what was actually read, and subtitles must come with the video.',
        'ask': '**Just tell me what you want to look up.** I will try to reuse existing logins first and open a window only when you really need to log in.',
        'public_default': "Try the agent's own public search and reading first.",
        'auth_note': 'Only when the chosen path for the remaining task actually requires authentication: reuse an authorized session first, then ask the user to log in; still verify the action after login.',
        'summary_head': "Use the agent's own public search and reading first; Reach adds capabilities as needed, and installing does not require logging in to each platform.",
        'summary_line': '{channel}: {public} Reach {actions} ({status}). {limits}',
        'evidence_note': 'Public-path notes come from samples and access conditions and do not replace local Reach acceptance; a network error, 403, timeout or captcha alone does not prove a login is needed.',
        'setup_failed': 'Install not finished: {code} {message}', 'report_saved': 'Full report saved: {path}',
        'report_write_error': 'Could not save the installation report; the full table is still in installation_report.markdown.',
        'reddit_login': 'Browser path only, if required',
    },
    'ja': {
        'greet_morning': 'おはようございます。何を調べましょう？☀️', 'greet_noon': 'こんにちは。何を調べましょう？',
        'greet_afternoon': 'こんにちは。何を調べましょう？', 'greet_evening': 'こんばんは。何を調べましょう？',
        'greet_night': '夜遅くまでお疲れさまです。何を調べましょう？🌙',
        'upgrade_title': '**今回は旧版（1.5）からのアップグレードです：**',
        'upgrade_kept': '- キーと設定はそのまま残しています。',
        'upgrade_web': '- RSS の購読と Exa のウェブ検索は単独の機能ではなくなりました。調べものとウェブページの読み取りは「ウェブ」にまとめています。',
        'upgrade_browser': '- Twitter や小紅書のようにログインが必要なプラットフォームは、Agent Reach 専用のブラウザを使うようになりました。初回は Chrome のログインの再利用をまず試します。',
        'upgrade_tools': '- 以前別に入れたコマンドラインツール（twitter-cli、bili など）はそのまま残しており、削除していません。',
        'upgrade_suggested': '- 以前 {names} を使っていました。続けて使うなら「XX を追加して」と言ってください。', 'list_sep': '、',
        'upgrade_removed': '- 旧版のプログラムは削除しました。今後新版とぶつかることはありません。',
        'upgrade_failed': '- 旧版のプログラムを削除できませんでした。次を実行してください：`{command}`',
        'done': 'のインストールが完了しました', 'almost': 'のインストールはあと一歩です',
        'headline': '**Agent Reach {version} {state}。** 標準の機能：{installed}/{total} 件の準備ができました。',
        'legend': '✅ ログイン不要／❌ ログインしてから試す／🔑 キーが必要／— 追加のログイン不要。',
        'table_head': '| プラットフォーム | ログインなしで調べられること | ログインしてから試すこと |',
        'install_failed': '（インストール失敗：{code}）', 'kept_removed': '（外したままにしています）', 'paren': '（{text}）',
        'verified': 'テスト済み：{names}。それ以外はまだ 1 つずつネットでテストしていません。', 'verified_sep': '／', 'name_sep': '：',
        'not_verified': 'まだ 1 つずつネットでテストしていません。',
        'sources': '要約・タイトル・リンクはまず検索エンジンから探します。コメントは実際に読めた分だけで、字幕は動画に付いているものだけです。',
        'ask': '**調べたいことをそのまま言ってください。** まず既存のログインの再利用を試し、本当にログインが必要なときだけウィンドウを開きます。',
        'public_default': '先に Agent 自身の公開の検索と読み取りを試す。',
        'auth_note': '残りのタスクで選んだ経路が実際に認証を求めたときだけ：まず認可済みのセッションを再利用し、次にユーザーにログインを頼む。ログイン後もアクションを確かめる。',
        'summary_head': '先に Agent 自身の公開の検索と読み取りを使う。Reach は必要に応じて機能を足す。インストールでプラットフォームごとのログインは要らない。',
        'summary_line': '{channel}：{public} Reach {actions}（{status}）。{limits}',
        'evidence_note': '公開経路の説明はサンプルとアクセス条件にもとづくもので、この PC での Reach の検収の代わりにはならない。ネットワークエラー・403・タイムアウト・CAPTCHA だけではログインが必要とは言えない。',
        'setup_failed': 'インストールは完了していません：{code} {message}', 'report_saved': 'レポートの全文を保存しました：{path}',
        'report_write_error': 'インストールレポートを保存できませんでした。表の全体は installation_report.markdown にあります。',
        'reddit_login': 'ブラウザ経由（必要なときだけ）',
    },
}


def text(key, **values):
    """One sentence in the current language."""
    return _TEXT[current_lang()][key].format(**values)


def _table(table):
    return table[current_lang()]


def _local_greeting():
    """Use the installing computer's clock and timezone, without a network lookup."""
    hour = datetime.now().hour
    if 5 <= hour < 11:
        return text('greet_morning')
    if 11 <= hour < 14:
        return text('greet_noon')
    if 14 <= hour < 18:
        return text('greet_afternoon')
    if 18 <= hour < 22:
        return text('greet_evening')
    return text('greet_night')

def _upgrade_lines(result):
    """Only for users coming from 1.5: what was kept, what changed, what is left to do."""
    migration = result.get('migration')
    if not migration:
        return []
    names = _table(_DISPLAY_NAMES)
    lines = [text('upgrade_title'), '',
             text('upgrade_kept'),
             text('upgrade_web'),
             text('upgrade_browser'),
             text('upgrade_tools')]
    suggested = [names.get(n, n) for n in migration.get('suggested_channels') or []]
    if suggested:
        lines.append(text('upgrade_suggested', names=text('list_sep').join(suggested)))
    old = result.get('old_copies') or {}
    if old.get('removed'):
        lines.append(text('upgrade_removed'))
    for item in old.get('failed') or []:
        from .legacy import manual_command
        lines.append(text('upgrade_failed', command=manual_command(item)))
    return lines + ['']



def installation_report(result):
    """Render one short receipt; keep detailed evidence in the structured summary."""
    def cell(value):
        return str(value).replace('|', r'\|').replace('\n', ' ')

    names = _table(_DISPLAY_NAMES)
    entries = result['capability_summary']['channels']
    installs = {row['channel']: row for row in result['default_channels']}
    installed = sum(bool(row['ok']) for row in installs.values())
    completed = all(row['ok'] for row in installs.values())
    lines = [
        _local_greeting(), '',
        text('headline', version=result['version'], state=text('done' if completed else 'almost'),
             installed=installed, total=len(installs)), '',
        *_upgrade_lines(result),
        text('legend'), '',
        text('table_head'), '|---|---|---|',
    ]
    for entry in sorted(entries, key=lambda item: item['level'] != 'default'):
        name = entry['channel']
        label = names.get(name, name)
        item = installs.get(name)
        if entry['level'] == 'default':
            if item and not item['ok']:
                label += text('install_failed', code=item.get('error', {}).get('code', 'UNKNOWN'))
            elif not item:
                label += text('kept_removed')
        elif entry['reach_status'] in {'needs_setup', 'needs_login', 'cooldown', 'needs_user_action', 'broken'}:
            label += text('paren', text=_table(_STATUS_LABELS)[entry['reach_status']])
        public, login = _table(_QUICK_ACCESS).get(name, (entry['public_access'], '—'))
        lines.append('| ' + ' | '.join(cell(value) for value in (label, public, login)) + ' |')
    verified = [entry for entry in entries if entry['verified_actions']]
    if verified:
        joined = text('verified_sep').join(names.get(entry['channel'], entry['channel']) + text('name_sep') +
                                           '/'.join(entry['verified_actions']) for entry in verified)
        lines += ['', text('verified', names=joined)]
    else:
        lines += ['', text('not_verified')]
    lines += [text('sources'), '',
              text('ask')]
    return '\n'.join(lines) + '\n'



def capability_summary(channels, statuses):
    """Describe public options, declared actions and local evidence without any I/O.

    Management supplies status records so this summary cannot initiate discovery,
    installation, login or a live request. Actions always come from the registry.
    """
    by_name = {entry['channel']: entry for entry in statuses}
    public_access = _table(_PUBLIC_ACCESS)
    limits_by_name = _table(_CAPABILITY_LIMITS)
    entries = []
    for ch in channels:
        current = by_name.get(ch.name, {})
        names = [action.name for action in ch.actions]
        can_login = bool(ch.login_url or ch.login_argv)
        auth_actions = {'bilibili': ['subtitle'], 'xueqiu': ['hot_posts', 'hot_stocks']}.get(
            ch.name, names if can_login else [])
        entries.append({
            'channel': ch.name,
            'level': ch.level,
            'reach_status': current.get('status', 'unverified'),
            'verified_actions': current.get('verified_actions', []),
            'actions': [{'action': action.name, 'detail': action.help} for action in ch.actions],
            'public_access': public_access.get(ch.name, text('public_default')),
            'authentication': {
                'when': 'only_if_required',
                'may_enable_actions': [name for name in auth_actions if name in names],
                'note': text('auth_note'),
            },
            'limits': limits_by_name.get(ch.name, []),
        })
    message = [text('summary_head')]
    for entry in entries:
        actions = '/'.join(action['action'] for action in entry['actions'])
        status_label = _table(_STATUS_LABELS).get(entry['reach_status'], entry['reach_status'])
        limits = ' '.join(entry['limits'])
        message.append(text('summary_line', channel=entry['channel'], public=entry['public_access'],
                            actions=actions, status=status_label, limits=limits))
    return {
        'policy': 'public_first; login_only_for_remaining_task_when_required',
        'evidence_note': text('evidence_note'),
        'channels': entries,
        'message': '\n'.join(message),
    }


def cdp_url():
    value = 'http://127.0.0.1:9222'
    return validate_cdp(value)


def validate_cdp(value):
    try:
        u = urlsplit(value)
        valid = (u.scheme == 'http' and u.hostname in {'localhost', '127.0.0.1', '::1'}
                 and u.port and not u.username and not u.password and not u.query
                 and not u.fragment and u.path in ('', '/'))
    except (TypeError, ValueError):
        valid = False
    if not valid:
        raise ReachError(BAD_INPUT, 'CDP must be a loopback HTTP address with an explicit port')
    return value.rstrip('/')


def cdp_status():
    url = cdp_url()
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(url + '/json/list', timeout=2) as resp:
            tabs = json.loads(resp.read(1024 * 1024))
        found = isinstance(tabs, list) and any(
            isinstance(t, dict) and t.get('type') == 'page'
            and host_matches(t.get('url', ''), 'zhipin.com') for t in tabs)
        return {'endpoint': url, 'connected': isinstance(tabs, list), 'boss_tab_present': bool(found)}
    except (OSError, ValueError):
        return {'endpoint': url, 'connected': False, 'boss_tab_present': False}


def require_boss_cdp():
    from . import browser, session_reuse
    session_reuse.prepare("boss")
    if not cdp_status()['boss_tab_present']:
        browser.open_url('https://www.zhipin.com/web/geek/jobs')
    browser.touch()
    return browser.CDP_URL
