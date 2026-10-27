# Capability scope

Read this when the user asks "what can it get / is it complete", or when you need to judge how complete a result is. The table below lists declared capabilities; it does not mean every network, account and piece of content has been tested.

## Three tiers

- **Public, worth trying**: the agent's existing web tools, native tools or public APIs may already cover the task; no browser install or login is required. Answer based on the evidence actually obtained.
- **Reach adds**: actions declared by the current release; see `agent-reach channels`. When configuration is needed, first reuse the session already saved in the dedicated browser; the user logs in themselves only when the chosen path actually requires login.
- **Verified on this machine**: list only the specific actions that recently passed acceptance on this machine. Installation, a saved session and network reachability do not equal functional acceptance.

## Channels in this release

| Channel | Public path worth trying | What Reach adds, and its limits |
|---|---|---|
| GitHub | Public repos, README, Issues/PRs | Repo search; reading repos/Issues/PRs and the comments returned; private access is judged separately |
| YouTube | Search, titles, descriptions; native tools may get some comments and subtitle text | search/read/subtitle/transcribe; no unified comments action for now; a track list is not subtitle text; when there are no subtitles, transcription depends on the corresponding tool |
| Bilibili (B站) | Search, descriptions; some public APIs return comments with parent/child IDs | search/read/hot/subtitle; no unified comments action for now; subtitles vary by video and access path |
| Reddit | Search, body, some comments; some public JSON includes parent/child IDs | Browser search/read/subreddit; whether login is needed depends on the chosen path; the full comment tree and all replies are not guaranteed; posting comments is not provided |
| X/Twitter | Public single posts hit by search; some official public embeds return the full text | search/profile/tweets/thread; a readable single post does not mean the reply stream is readable; the full comment tree is not guaranteed |
| Xiaohongshu (小红书) | Public lists or indexes may have note ID, author and title; empty fields must not be filled in by guessing | search/read/comments; text description, top-level comments and replies already loaded; all comments are not guaranteed; never claim to understand images/video |
| Instagram | Some indexed and shallow profile info; the HTML app shell does not count as a post | search finds users, profile for the profile page, posts for a given user's post descriptions; no unified comments action; never claim to understand images/video |
| Facebook | Some indexed or HTML snippets; snippets may be truncated | search/profile; no unified detail or comments action; do not treat search snippets as full text |
| LinkedIn | Search public jobs, read public JDs | jobs/read try the public web first; only when opencli is specified do they go straight to the site; not every job is guaranteed readable |
| BOSS (Boss直聘) | Search indexes may have job summaries | search/read job lists and JDs; never guess numbers from an encoded salary; the fallback for details depends on what the channel declares |
| V2EX | Topics, body and public replies | hot/node/read/user; the scope is whatever this response returns; hidden or missing replies are not guaranteed |
| Xueqiu (雪球) | Some public quotes and index info | quote/search/hot_posts/hot_stocks; the quote path and the community path are verified separately |
| Web | The agent's built-in search/read | Reach web search/read is the anonymous fallback; snippets, page shells and verification pages cannot be treated as full body text |
| Xiaoyuzhou (小宇宙) | Episode page title and description | transcribe turns a whole episode into text; needs a Groq key from the user (`agent-reach configure groq-key`) |

When describing capabilities after login, say "can enable / try the browser actions above"; do not say "supports all comments after login". If the user skips login, deliver the public evidence already gathered.
