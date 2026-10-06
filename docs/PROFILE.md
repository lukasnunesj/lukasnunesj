# Profile maintenance

The README is a GitHub Profile, not a website. It uses GitHub-supported Markdown, HTML tables, `<details>`, and `<picture>` elements. There is no build step and no npm install requirement for the profile.

## Preview and checks

Open `README.md` in VS Code and use **Markdown: Open Preview** (`Ctrl+Shift+V`). Theme switching uses the viewer's `prefers-color-scheme`. Check both light and dark themes. SVGs can also be opened directly in a browser.

Run the focused checks without installing dependencies:

```sh
python3 -m unittest discover -s scripts -p 'test_*.py'
git diff --check
```

If `actionlint` is available, run `actionlint .github/workflows/profile-assets.yml`.

GitHub's actual README rendering is the final reference; a local editor may render tables and theme selection differently.

## Dynamic assets

`.github/workflows/profile-assets.yml` generates versioned SVGs in `assets/`:

| Asset | Source | Schedule |
| --- | --- | --- |
| Contribution snake, light/dark | Platane/snk, GitHub contributions | Daily at 03:17 UTC |
| Public code card, light/dark | GitHub REST API, public original repositories only | Daily at 03:17 UTC |
| Spotify card, light/dark | Spotify Web API | Every 30 minutes |

The public code chart counts primary repository languages, not lines of code or professional proficiency. Forks and private repositories are excluded. The timestamp identifies the last successful refresh.

The workflow also supports `workflow_dispatch`. A push changing the generator or workflow on `master` starts a full refresh. Scheduled workflows only run on the default branch. Manual runs on other branches are deliberately skipped.

The public repository card and asset publication use this repository's `GITHUB_TOKEN`. The snake uses the existing `GH_TOKEN` repository secret, authenticated as the profile owner, to include private contribution counts. The built-in repository token can omit those counts even when the public profile displays them. No private repository names or source code are published. The job has `contents: write` because it commits generated assets back to the default branch; no other permissions are granted. The actions are pinned to verified release SHAs:

- [actions/checkout v7.0.1](https://github.com/actions/checkout/releases/tag/v7.0.1)
- [Platane/snk v3.5.0](https://github.com/Platane/snk/releases/tag/v3.5.0), SVG-only action

There are no npm dependencies. The snake reuses the already configured `GH_TOKEN`; its credential must remain valid. Do not delete this secret while the snake uses it. It publishes only the six generated cards, not the README or header. Runs are serialized; pushes are normal fast-forward pushes, never forced. An unrelated push during a run may cause a safe failure; rerun the workflow.

GitHub schedules are best effort and can be delayed. Scheduled workflows in inactive public repositories can be disabled after 60 days. Re-enable the workflow in Actions if needed. Spotify is a dated snapshot, not an instantaneous now-playing widget. Refreshes can create bot commits; only changed assets are committed.

### Enable GitHub refreshes

After these files are committed and pushed by the repository owner:

1. Check **Settings → Actions → General** and allow the pinned actions.
2. Run **Actions → Profile assets → Run workflow** on `master`.
3. If branch rules block `github-actions[bot]`, allow this workflow to update generated assets or adapt publication to a separate branch. The workflow intentionally does not bypass branch protection.

Initial snake and public code SVGs were generated from real GitHub data during implementation, so the README has valid local images before the first hosted run.

## Spotify setup

### What was broken

The old Novatorem URL redirects to the hyphenated Vercel deployment, which returned HTTP 500 during the audit. The fork is from 2020 and pins Flask 1.1.2 and requests 2.24.0. Its Spotify code assumes a successful token response, mishandles null tracks, and assumes recent history is nonempty. The exact production exception cannot be determined without deployment logs. This repository does not modify the Novatorem fork or its deployment.

The replacement calls Spotify directly from Actions and generates native SVGs. It requires no Vercel deployment or public widget service. No track, artist, or listening activity is fabricated while authorization is missing.

### Required repository secrets

In **Settings → Secrets and variables → Actions → New repository secret**, add:

| Secret | Value |
| --- | --- |
| `SPOTIFY_CLIENT_ID` | The client ID from your Spotify developer app |
| `SPOTIFY_CLIENT_SECRET` | The app's client secret |
| `SPOTIFY_REFRESH_TOKEN` | A refresh token authorized by your Spotify account |

The old Novatorem name `SPOTIFY_SECRET_ID` maps to the new `SPOTIFY_CLIENT_SECRET`. If you can still access the old deployment's environment settings, reuse its values securely, provided the app and authorization are still valid. GitHub's existing `GH_TOKEN` and `WAKATIME_API_KEY` do not provide Spotify access.

If a new authorization is needed:

1. Create or open an app in the [Spotify developer dashboard](https://developer.spotify.com/dashboard).
2. Check the current [development-mode requirements](https://developer.spotify.com/documentation/web-api/concepts/quota-modes). Spotify currently requires an active Premium account for the app owner in development mode, and authorized users must be allowed by the app. Do not assume a 2020 app's access remains valid.
3. Register a loopback redirect URI such as `http://127.0.0.1:8888/callback`. The URI used for authorization and token exchange must match the registered value exactly. Follow Spotify's [redirect URI rules](https://developer.spotify.com/documentation/web-api/concepts/redirect_uri).
4. Follow the official [Authorization Code flow](https://developer.spotify.com/documentation/web-api/tutorials/code-flow), requesting both `user-read-currently-playing` and `user-read-recently-played`. Generate and verify the OAuth `state` value. Exchange the returned authorization code at `https://accounts.spotify.com/api/token` using the app credentials and matching redirect URI. Store the returned `refresh_token` as the repository secret above.
5. Run **Profile assets** manually. A playing music track is shown as **Playing at last check**. When paused, stopped, or playing a podcast, the card falls back to the latest music track from recent history. Empty history is handled without failing.

### Local authorization helper

After registering `http://127.0.0.1:8888/callback` in the Spotify app, run:

```sh
python3 scripts/spotify_authorize.py
```

The helper asks for Client ID and Client Secret without echoing them, opens the browser, receives the loopback callback, validates OAuth state and PKCE, and exchanges the code. You still need to approve Spotify access in the browser. It times out after five minutes and binds only to `127.0.0.1`.

Only the refresh token is printed to stdout on success. Prompts and instructions go to stderr. Errors return a nonzero exit status without printing Spotify response bodies. It does not save credentials, set GitHub secrets, or modify any repository. Copy the returned token into the `SPOTIFY_REFRESH_TOKEN` repository secret. Run the helper locally, never in Actions or a shared terminal recording.

Keep credentials out of the repository, screenshots, issues, and Actions logs. A missing configuration shows a connection-pending card. A partial configuration fails with a safe error. HTTP failures preserve the last successful, timestamped snapshot and make the workflow report failure; other successfully generated assets can still be published. A Spotify 401 usually requires reviewing the app credentials or renewing authorization; a 403 may indicate app access restrictions or missing scopes.

The widget links to Spotify, not to an assumed account username. The legacy README's username differed from the GitHub handle, so it was not reused without verification.

## Audit and project selection

Inspected the complete working README and committed legacy README, all tracked files, Git history, workflows, the legacy CLI, public repository metadata, candidate READMEs, and representative source files.

- Removed WakaTime output and its workflow: last committed statistics were from February 2023; no current successful integration was established. The old action followed mutable `master` and depended on an extra PAT.
- Removed `charts/bar_graph.png`: generated by the retired WakaTime integration and referenced only by the old README. Its last update was February 2023.
- Replaced the previous green header with original cosmic/terminal headers for both themes.
- Removed the expired website link everywhere in this repository. Removed the old employer/title from the CLI without refactoring it.
- Preserved `src/`, `lib/`, `package.json`, and `yarn.lock`: these implement the separately published `lucasnunesj` CLI, not README generation. Dependencies remain legacy; the package's `test` is an interactive demo, not a regression suite. No CLI dependency installation or npm publication was performed.

Selected four original projects after inspecting their public code:

- **demotivational-coach:** Rails controller serves random demotivational JSON messages. Its README is generic, but the source substantiates the memorable premise.
- **a_simple_experimental_database:** C CLI with B-tree operations and disk persistence. Presented as a learning experiment, not a production database.
- **MouseGlowStarEffect:** browser cursor/touch star effect; its palette already fits this profile's visual interests. Linked to source rather than assuming the old hosted demo is alive.
- **biblioteca-a7:** more recent Java/Jakarta EE REST API and Swing client, PostgreSQL, and architecture documentation. Described technically without making job searching central to the profile.

Other candidates were considered: `Generative-Art` has a small canvas experiment but no README; `bookfindr` is a Vue/Google Books study; `ScrumPoker` and `word-of-the-day` lack root READMEs. `ai-job-search` is a fork of MadsLorentzen's project; `enigma_do_medo` is also a fork. They were not presented as original work or chosen over the four above.

### Widget decisions

The snake plus public code card are the only two GitHub visualizations. Spotify adds a personal dynamic component. Custom assets share the same midnight/cyan/indigo palette and have light variants.

Checked current maintenance metadata for github-readme-stats, streak stats, typing SVG, the activity graph, profile summary cards, and lowlighter/metrics. Several remain active; github-readme-stats also answered HTTP 200 during the audit. They were omitted for composition and lower dependency count, not labeled universally broken. No trophies, visitor counter, dynamic badges, or third-party typing widget are used. No copyrighted game/anime assets are included.

## Upstream documentation

- [snk usage, colors, and theme variants](https://github.com/Platane/snk)
- [Checkout action and token permissions](https://github.com/actions/checkout)
- [GitHub workflow syntax and permissions](https://docs.github.com/en/actions/writing-workflows/workflow-syntax-for-github-actions)
- [GitHub schedule behavior](https://docs.github.com/en/actions/writing-workflows/choosing-when-your-workflow-runs/events-that-trigger-workflows#schedule)
- [GitHub image theme selection](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/using-pictures-in-markdown)
- [Spotify token refresh](https://developer.spotify.com/documentation/web-api/tutorials/refreshing-tokens)
- [Spotify currently playing](https://developer.spotify.com/documentation/web-api/reference/get-the-users-currently-playing-track)

Release and endpoint checks were performed during implementation in October 2026. Future action upgrades should verify the current release and update the pinned SHA deliberately.

## Validation record

- Seven standard-library tests pass: public/fork/private selection, playback states, XML escaping, both themes, missing/partial credentials, authenticated request sequence, and safe HTTP failure behavior.
- `actionlint` v1.7.12 passes; its downloaded release archive was checksum-verified. No global tooling was installed.
- The GitHub Markdown API preserved all four `<picture>` blocks, eight theme sources, project tables, and the collapsible stack section. All local SVGs parse and all referenced image paths exist.
- Headers and cards were rendered and inspected in both themes. The animated snake was executed from the pinned upstream release using real GitHub contribution data; its CSS animation requires a browser to play.
- Every GitHub/project URL and the Spotify destination returned HTTP 200. LinkedIn returned HTTP 999 to an automated request, so its page could not be independently checked; the URL supplied by the profile owner is preserved.
- Legacy JavaScript syntax and `git diff --check` pass. The legacy CLI itself was not rerun with installed dependencies.
- Hosted Actions execution and an authenticated Spotify playback request remain unverified: publication is explicitly out of scope, and Spotify secrets are not configured. These are activation steps, not successful live integrations claimed by this change.

`GH_TOKEN` is required by the snake. The retired `WAKATIME_API_KEY` is unused and may be removed manually after reviewing whether anything outside this repository relies on it.
