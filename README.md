# Erika Market Directory

This project turns the Erika market dataset into a static directory site designed for GitHub
Pages. It behaves like a searchable catalog, with a landing page for discovery and a dedicated
profile view for individual listings.

## Architecture

- **Astro static site** for presentation and page generation
- **Python build step** that reads `../../erika/artifacts/ticker_checklist.csv`
- **Static JSON catalog** served from `public/data/catalog.json`
- **Server-rendered summary data** written to `src/generated/catalog-meta.json`

The site does not require a runtime backend. Search and filtering happen in the browser against
the generated JSON catalog.

## Local development

```bash
npm install --cache .npm-cache
npm run dev
```

The data-prep step runs automatically before `dev` and `build`.

## Build

```bash
npm run build
```

The production site is generated in `dist/`.

## GitHub Pages

The Astro config auto-detects the correct base path during GitHub Actions builds:

- user/org pages: `/`
- project pages: `/<repo-name>/`

If you need to override it manually, set `PUBLIC_BASE_PATH`.

The deployment workflow is in `.github/workflows/deploy.yml`.

## Data refresh

When the Erika source CSV changes, rebuild the site:

```bash
npm run prepare:data
npm run build
```

## Source data

- `../../erika/artifacts/ticker_checklist.csv`
- `../../erika/artifacts/ticker_checklist_summary.md`

The directory currently focuses on listing metadata and coverage signals, not time-series charting.
