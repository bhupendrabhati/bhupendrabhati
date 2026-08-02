# Chat Log & Decisions — GitHub Profile Build

Complete running log of every conversation, decision and change for Bhupendra
Bhati's animated GitHub profile (`bhupendrabhati/bhupendrabhati`, branch
`main`). This file is updated after every session — never delete the history.

## Context

- Project: complete animated GitHub profile — banner, stats cards, contribution
  snake, social badges, project panel — per `Prompt.md`.
- The `arifhaxn/` directory is a **reference-only** copy of Arif Hasan's setup.
  It is used to study the banner structure and must **never be pushed**
  (excluded via `.gitignore`).
- Local banner pipeline: `pipeline.py` (portrait + logo data),
  `generate_banner.py` (dark.svg / light.svg), workflows for the snake and the
  projects panel.

---

## Session 1 — Assessment & plan (suggestions accepted)

**What was discussed**

1. The profile repo already had: an assembled `README.md`, a banner pipeline
   (`.github/scripts/banner/pipeline.py`), workflows for snake + projects
   (`snake.yml`, `projects.yml`), a source `portrait.png`, and logo SVGs.
2. Assessment found:
   - `projects.json` was empty (`[]`), so the project panel rendered blank.
   - Root `dark.svg` / `light.svg` were small 6 KB placeholders, not the real
     animated banner (the ~1 MB animated version exists only in `arifhaxn/`).
   - Nothing was committed yet except `README.md`; `arifhaxn/`, `.DS_Store`,
     `BB.png` and other files were untracked and at risk of being pushed.
   - Workflows need repo **Actions → Workflow permissions → Read and write**.
3. Repo scan of `bhupendrabhati` produced the real project list used to fill
   `projects.json` (IndraNet, SankalanTab, AI-CLI, BB-CloudSight,
   bhupendrabhati-portfolio, KALATHMIKA, DMI-LMS-Infra-001, epicbook-terraform,
   Bhupen-AI-Agent, KALATHMIKA-ARCHITECTURAL-STUDIO, CodeEditorPlugins, etc.).

**Suggestions (all accepted by Bhupendra)**

1. Add `.gitignore` excluding `arifhaxn/`, `.DS_Store`, `.venv/`, `BB.png`.
2. Generate the real animated banner (dark + light) from `portrait.png` via
   the banner pipeline, replacing the 6 KB placeholders.
3. Fill `projects.json` with the real repo data so the project panel works.
4. Commit + push, then enable Actions workflow permissions (Settings → Actions →
   General → Workflow permissions → Read and write).
5. (Optional) Self-host stats — fork `anuraghazra/github-readme-stats` and
   deploy on the free Vercel hobby tier with a classic PAT (`repo` scope).

**Work done in Session 1**

- [x] Investigated repo state (`git status`, structure, workflow files).
- [x] Studied the reference banner structure from `arifhaxn/` (defs, 60 intro
      groups, ~94 drift bands, 900 travellers, info panel, chrome).
- [x] Fetched live repo data from GitHub API for `projects.json`.
- [x] Created this `chat.md` and `.gitignore`.
- [x] Fixed `pipeline.py` (dot-density scaling ~17k dark / ~39k light, logo
      rasterization via cairosvg) and regenerated `data/portrait.npz` +
      `data/logos.npz` (12 logos: ansible, aws, azure, devops, docker, gcp,
      git, jenkins, kubernetes, linux, terraform, vercel).
- [x] Wrote `generate_banner.py` → real animated `dark.svg` (~912 KB) /
      `light.svg` (~1.3 MB), replacing the 6 KB placeholders.
- [x] Validated the banner: 60 intro groups, ~96/~90 drift bands, 900
      travellers, morph targets in-bounds, cairosvg render OK for both themes.

---

## Session 2 — Ship the base build

**Work done**

- [x] Filled `projects.json` (12 repos) and verified the fetch_data.py +
      generate_projects.py pipeline end-to-end locally (live stars /
      languages / pushed_at merged; both theme SVGs render).
- [x] Committed and pushed everything (commit `a0ba145`, 28 files).
- [x] Enabled Actions workflow permissions to **read/write** via the GitHub
      API (Settings equivalent). Both Actions ran green and pushed
      `projects/projects.svg`, `output/snake-dark.svg`, `output/snake-light.svg`.

---

## Session 3 — AWS-only visual

**User feedback:** "In the Visual.map my image is good but the rest is not
visible. I want you to add visual for AWS only."

**What we found & did**

- The logo morph used 900 `<use>` rects driven by SMIL `animateTransform`,
  which did not render on the profile (the portrait, drawn as `<path>` dot
  groups, rendered fine).
- Replaced the travellers with the AWS wordmark drawn as a `<path>` dot layer
  — the same mechanism as the portrait, so it renders reliably — scaled 1.2x
  and centered in the frame (px 133–340 × 267–412), fading in while the
  portrait fades out on the 13.9s loop. Azure/GCP cycle removed.
- Files dropped to ~494 KB (dark) / ~889 KB (light). Committed as `a948e89`.

---

## Session 4 — Four cloud logos

**User feedback:** "Now add azure gcp and DevOps too."

**What we did**

- Extended the path-based logo layer to AWS, Azure, GCP and DevOps. Each logo
  is scaled to fit ~175x118 grid units (aspect preserved), centred in the
  frame, and gets its own slot in the 13.9s loop (keytimes 0.30–0.435 /
  0.435–0.57 / 0.57–0.705 / 0.705–0.90) with quick cross-fades. Portrait stays
  hidden during the logo window.
- Files ~516 KB (dark) / ~911 KB (light). Committed as `0cd6dbb`.

---

## Session 5 — Name labels, social badges, running chat log

**User feedback:**

1. "Below Azure GCP Github DevOps visual write their name also (e.g. below
   Azure logo write Azure, below GitHub logo write GitHub)."
2. "Remove X and Facebook. Keep only LinkedIn, Medium, Email — use icons only,
   no black background."
3. Keep this `chat.md` file with all chat and suggestions from the beginning
   to the end of every session, updated every time.

**Decisions**

- Clarified with Bhupendra: do **not** replace any logo — keep AWS, Azure,
  GCP, DevOps and just add each logo's name below it.
- Logo name labels (AWS / AZURE / GCP / DEVOPS) added below the visuals in the
  VISUAL.MAP frame, fading in/out in sync with each logo's slot.
- Corrected the fourth visual slot label from **DEVOPS** to **GITHUB** after
  confirming that slot is the GitHub icon.
- Added a separate **DevOps** visual slot with its own **DEVOPS** label so both
  GitHub and DevOps now appear independently in the visual cycle.
- Refined the DevOps visual from a text-only placeholder into an icon treatment,
  then updated it again to an **infinity-loop DevOps** style so it reads more
  like a real DevOps symbol in the VISUAL.MAP frame.
- Fixed broken **GitHub Stats** and **Top Languages** cards in `README.md` by
  switching from the failing `github-readme-stats.vercel.app` public endpoint
  (returning 503) to the working `github-readme-stats-sigma-five.vercel.app`
  mirror.
- README social badges reduced to **LinkedIn, Medium, Email** only (X and
  Facebook removed). All three are icon-only (`for-the-badge` with an empty
  label), on brand colors, no black background:
  - LinkedIn `#0A66C2` (logo supplied as an encoded data-URI because the
    `linkedin` icon slug is unavailable on shields.io)
  - Medium `#00AB6C`
  - Gmail `#EA4335`
- Rewrote this file as the full session-by-session log.

---

## Manual steps (for Bhupendra)

- [ ] (Optional) Create classic PAT (`repo` scope), fork
      `anuraghazra/github-readme-stats`, deploy on Vercel Hobby with `PAT_1`.
- [ ] The snake `<picture>` block is already in the README; it renders now that
      the `output` branch exists.

## Reference data points (editable)

- Email: `bhupendrabhati05@gmail.com`
- Title: `bhupendrabhati05@gmail.com - % ./profile.sh --live`
- Role: Cloud DevOps Engineer · Origin: Jaipur, India
- Education: B.Tech. I.T., PG in Cloud Computing
- LinkedIn `bhupendrabhati` · GitHub `@bhupendrabhati` · Medium
  `@bhupendrabhati` · Facebook `PalEkHaseenLamha`
