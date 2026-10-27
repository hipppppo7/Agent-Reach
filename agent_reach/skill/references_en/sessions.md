# Sessions and the dedicated browser

Read this when the user wants to log in, log out or switch accounts, or when a result returns `NEED_LOGIN`.

## Dedicated browser

- All browser channels share one dedicated browser profile, separate from the user's everyday Chrome; the program never closes or modifies the user's everyday browser.
- CloakBrowser is the preferred engine; if downloading or installing it fails, the locally installed Chrome is used, and this fallback is remembered so it is not re-downloaded every time. Once the network is fixed, retry with `agent-reach browser setup --retry-cloak`.
- `agent-reach add <channel>` automatically prepares Node, OpenCLI, the engine and the extension. Tools are installed at the versions tested for this release. On Windows with the Chrome fallback, the user may need to click "Add to Chrome" once.
- Headless by default, no window. Only `agent-reach login <channel>` shows a window; while that window is open, queries use it directly and do not close it. While the user is logging in, wait until the user says they are logged in before querying. After the window is closed, later queries go back to headless.
- It closes automatically after 10 idle minutes and reopens on the next call; real page interactions and Reach calls reset the timer. During login the session is saved periodically, so the user does not need to close the window.
- Parallel calls are allowed: up to 2 at once per platform and 4 in total across all platforms; the rest wait in line for at most 2 minutes, and `BUSY` is returned only if they still cannot run. Two searches on the same platform start at least 10 seconds apart. Opening a login window, logging out and reinstalling the browser wait for running queries to finish first.
- `agent-reach browser status` shows status, `browser setup` prepares the engine and extension, `browser stop` closes the browser the program manages.

## Automatically reusing an existing login

1. The first time a site is used, if the user's Chrome is connected to the OpenCLI extension, the program copies that site's login (that site's cookies only) once into the dedicated browser. It does not copy the whole browser directory, other sites or the password store, and does not modify the source browser.
2. After a successful copy, the saved session is reused from then on; it is not re-copied on a timer. Cookies being present does not mean the login is valid; the result of a real action decides.
3. When the user's Chrome is not connected to the extension, do not promise automatic reuse, and do not conclude from this that the user is not logged in; in that case Reach's saved session is used.
4. When several browsers on this machine are logged in to the site: `agent-reach browser profiles` lists the sources and `agent-reach browser use <ID>` picks one; do not switch at random.
5. `agent-reach login <channel> --import-existing` actively re-copies that site's login once, without opening a window.
6. Once the user has logged in themselves in the dedicated window, or has run `logout` / `remove`, automatic copying stops, so a logged-out session is not brought back to life.

## When the user must log in themselves

- Ask the user to log in only when `NEED_LOGIN` is actually returned and the remaining task really needs that path. A login button next to the body text does not count as requiring login.
- `agent-reach login <channel>` opens the dedicated browser at the site's login page, and the user completes the login themselves. You never log in for them, never ask for a password, never print cookies.
- If `next` in the result lists follow-up steps, follow them; some native-tool channels (such as Xueqiu (雪球)) need `agent-reach login <channel> --sync` after login.
- After the user finishes, run the original action again to verify.

## Platform differences

- Boss Zhipin (Boss直聘) in-site search goes through OpenCLI and shares the dedicated browser. If a job detail asks for login because of an upstream false report, do not make the user log in again and again.
- Bilibili (B站) hands the existing login to Bilibili's official command-line tool only when reading subtitles; ordinary search does not prepare a browser.
- Xueqiu (雪球) community actions need login; the session expires within a few hours, after which the login steps are repeated.

## Logging out and removing

- `agent-reach logout <channel>`: clears that site's login and the channel's own state in the dedicated browser; other sites are kept.
- `agent-reach remove <channel>`: removes the channel and also clears that site's login and storage; other sites are kept. If cleanup fails, the channel record is kept and an error is returned so the user can retry.
- After either, that site's login is no longer copied automatically.
