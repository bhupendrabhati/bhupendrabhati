# Chat Log & Decisions — GitHub Profile Build

Living log of the session building Bhupendra Bhati's animated GitHub profile
(`bhupendrabhati/bhupendrabhati`, branch `main`).

## Context

- Project: complete animated GitHub profile — banner, stats cards, contribution
  snake, social badges — per `Prompt.md`.
- The `arifhaxn/` directory is a **reference-only** copy of Arif Hasan's setup.
  It is used to study the banner structure and must **never be pushed**.

## What we discussed

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

## Suggestions (all accepted by Bhupendra)

1. **Add `.gitignore`** excluding `arifhaxn/`, `.DS_Store`, `.venv/`, `BB.png`.
2. **Generate the real animated banner** (dark + light) from `portrait.png`
   via the banner pipeline, replacing the 6 KB placeholders.
3. **Fill `projects.json`** with the real repo data so the project panel works.
4. **Commit + push, then enable Actions workflow permissions** (Settings →
   Actions → General → Workflow permissions → Read and write) so the CI
   workflows can push the `projects` / `output` branches.
5. **(Optional) Self-host stats** — fork `anuraghazra/github-readme-stats` and
   deploy on the free Vercel hobby tier with a classic PAT (`repo` scope) to
   avoid the public instance's rate limits.

## Work log

- [x] Investigated repo state (`git status`, structure, workflow files).
- [x] Studied the reference banner structure from `arifhaxn/` (defs, 60 intro
      groups, ~94 drift bands, 900 travellers, info panel, chrome).
- [x] Fetched live repo data from GitHub API for `projects.json`.
- [x] Created this `chat.md` and `.gitignore`.
- [x] Fixed `pipeline.py` (dot-density scaling ~17k dark / ~39k light, correct
      logo rasterization via cairosvg) and regenerated `data/portrait.npz` +
      `data/logos.npz` (12 logos: ansible, aws, azure, devops, docker, gcp,
      git, jenkins, kubernetes, linux, terraform, vercel).
- [x] Wrote `generate_banner.py` → real animated `dark.svg` (~912 KB) /
      `light.svg` (~1.3 MB), replacing the 6 KB placeholders.
- [x] Validated the banner: 60 intro groups, ~96/~90 drift bands, 900
      travellers, morph targets in-bounds, cairosvg render OK for both themes.
- [x] Filled `projects.json` (12 repos) and verified the fetch_data.py +
      generate_projects.py pipeline end-to-end locally (live stars /
      languages / pushed_at merged; both theme SVGs render).

## Manual steps (for Bhupendra)

- [ ] Repo Settings → Actions → General → Workflow permissions → **Read and write**.
- [ ] (Optional) Create classic PAT (`repo` scope), fork
      `anuraghazra/github-readme-stats`, deploy on Vercel Hobby with `PAT_1`.
- [ ] Add the snake `<picture>` block to the README only after the snake Action
      runs green (the `output` branch must exist first).
