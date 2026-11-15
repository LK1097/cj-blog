# C&J Property Assessments blog

Static blog for https://blog.candjpropertyassessments.com, deployed by Cloudflare Pages.

- `posts/<slug>.md` — one article per file (YAML frontmatter + Markdown/HTML body). The URL is `/<slug>`.
- `static/` — images (WebP) and favicon.
- `python3 build.py` — builds `dist/` (pages, sitemap.xml, robots.txt, llms.txt). **Run it and commit `dist/` with every change.**
- Cloudflare Pages settings: production branch `main`, no build command, output directory `dist`.
- `content-log.md` — running log of articles written or refreshed by Claude.
