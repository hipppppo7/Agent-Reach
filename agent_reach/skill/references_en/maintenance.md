# Maintenance

Read this when an update fails, the browser will not start, a channel reports errors, or the user wants to uninstall.

- Update: `agent-reach update` upgrades Agent Reach, the tools of added channels and the skill; `agent-reach update --check` only checks whether a new version exists. Run it only after the user agrees.
- Status: `agent-reach doctor --text` reads local status without going online; `agent-reach check <channel> --text` runs one live test online (`--search` tests only search/jobs). A successful install does not mean the live test passes.
- Browser: `agent-reach browser status` shows status, `browser setup` prepares the engine and extension, `browser stop` closes it; after a CloakBrowser download failure, once the network is fixed, run `browser setup --retry-cloak`.
- Tell failure stages apart: dependency download, browser connection, login, page loading and platform rate limiting are each separate; do not describe a network timeout as an expired login.
- Upstream tool errors: note the error and the version, and run `agent-reach update` once after the user agrees; do not modify the upstream tool's installed files, and do not retry in a loop.
- `PLATFORM_BLOCKED`, `RATE_LIMITED`, `NEED_LOGIN`, `BUSY`: stop this attempt and continue only after the user has dealt with it; do not open windows repeatedly.
- Keys and proxy: `agent-reach configure groq-key | openai-key | proxy | github-token`; the values are provided by the user themselves.
- Uninstall: first show the user the scope with `agent-reach uninstall --dry-run`, then run `agent-reach uninstall` after they confirm. Only what Reach itself installed is removed; the user's other files and browsers are kept.
