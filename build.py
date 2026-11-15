#!/usr/bin/env python3
"""Build the C&J blog: posts/*.md -> dist/ (static HTML, sitemap, robots, llms.txt).

Each post is Markdown (raw HTML allowed) with YAML frontmatter:
  title, description, date (YYYY-MM-DD), slug, keywords (list),
  updated (optional), faq (optional list of {q, a}), image (optional, /static/...webp), image_alt
Run:  python3 build.py
"""
import html, json, pathlib, shutil, datetime, re
import markdown, yaml

SITE = "https://blog.candjpropertyassessments.com"
MAIN = "https://candjpropertyassessments.com"
NAME = "C and J Property Assessments"
ROOT = pathlib.Path(__file__).parent
POSTS, STATIC, DIST = ROOT / "posts", ROOT / "static", ROOT / "dist"

CSS = """
:root{--ink:#1d2430;--muted:#5b6575;--line:#e3e6ea;--accent:#1f4e79;--bg:#fbfaf7}
*{box-sizing:border-box}body{margin:0;font:17px/1.65 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:var(--ink);background:var(--bg)}
a{color:var(--accent)}header,footer{background:#fff;border-bottom:1px solid var(--line)}footer{border-top:1px solid var(--line);border-bottom:0;margin-top:64px}
.wrap{max-width:760px;margin:0 auto;padding:0 20px}.bar{display:flex;justify-content:space-between;align-items:center;padding:14px 0;gap:12px;flex-wrap:wrap}
.brand{font-weight:700;text-decoration:none;color:var(--ink)}.cta{background:var(--accent);color:#fff;padding:8px 14px;border-radius:6px;text-decoration:none;font-weight:600;font-size:15px}
h1{font-size:2.1rem;line-height:1.2;margin:40px 0 8px}h2{margin-top:2.2em;line-height:1.3}h3{margin-top:1.6em}
.meta{color:var(--muted);font-size:14px;margin-bottom:28px}img{max-width:100%;height:auto;border-radius:6px}
table{border-collapse:collapse;width:100%;font-size:15px}th,td{border:1px solid var(--line);padding:8px;text-align:left;vertical-align:top}
.card{display:block;padding:18px 0;border-bottom:1px solid var(--line);text-decoration:none;color:var(--ink)}.card h2{margin:0 0 4px;font-size:1.2rem;color:var(--accent)}.card p{margin:0;color:var(--muted);font-size:15px}
aside{display:block;background:#fff;border-left:4px solid var(--accent);padding:12px 18px;margin:24px 0;border-radius:4px}
.box{background:#fff;border:1px solid var(--line);border-radius:8px;padding:20px;margin-top:40px}.small{font-size:14px;color:var(--muted)}
"""


def esc(s):
    return html.escape(str(s or ""), quote=True)


def page(title, desc, canonical, body, jsonld=(), og_type="website", image=None):
    ld = "".join(f'<script type="application/ld+json">{json.dumps(x, ensure_ascii=False)}</script>' for x in jsonld)
    img = f'<meta property="og:image" content="{SITE}{esc(image)}">' if image else ""
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title><meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{esc(canonical)}">
<meta property="og:type" content="{og_type}"><meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}"><meta property="og:url" content="{esc(canonical)}">{img}
<link rel="icon" href="/static/favicon.png"><style>{CSS}</style>{ld}</head><body>
<header><div class="wrap bar"><a class="brand" href="/">{NAME} &middot; Blog</a>
<a class="cta" href="{MAIN}">Request a quote</a></div></header>
<main class="wrap">{body}</main>
<footer><div class="wrap bar small"><span>&copy; {datetime.date.today().year} {NAME} &middot; Commercial property condition assessments in North Carolina, Virginia and South Carolina</span>
<a href="{MAIN}">candjpropertyassessments.com</a></div></footer></body></html>"""


def load_posts():
    posts = []
    for f in sorted(POSTS.glob("*.md")):
        raw = f.read_text(encoding="utf-8")
        m = re.match(r"^---\n(.*?)\n---\n(.*)$", raw, re.S)
        if not m:
            raise SystemExit(f"{f.name}: missing frontmatter")
        fm, body = yaml.safe_load(m.group(1)) or {}, m.group(2)
        for k in ("title", "description", "date"):
            if not fm.get(k):
                raise SystemExit(f"{f.name}: missing '{k}'")
        fm["slug"] = fm.get("slug") or f.stem
        fm["date"] = str(fm["date"])
        fm["updated"] = str(fm.get("updated") or fm["date"])
        fm["body_html"] = markdown.markdown(body, extensions=["tables", "fenced_code", "md_in_html"])
        posts.append(fm)
    slugs = [p["slug"] for p in posts]
    dupes = {s for s in slugs if slugs.count(s) > 1}
    if dupes:
        raise SystemExit(f"duplicate slugs: {dupes}")
    return sorted(posts, key=lambda p: p["date"], reverse=True)


def render_post(p):
    url = f"{SITE}/{p['slug']}"
    faq = p.get("faq") or []
    faq_html = ""
    ld = [{"@context": "https://schema.org", "@type": "BlogPosting", "headline": p["title"],
           "description": p["description"], "datePublished": p["date"], "dateModified": p["updated"],
           "mainEntityOfPage": url, "author": {"@type": "Organization", "name": NAME, "url": MAIN},
           "publisher": {"@type": "Organization", "name": NAME, "url": MAIN}}]
    if faq:
        faq_html = "<h2>Frequently asked questions</h2>" + "".join(
            f"<h3>{esc(x['q'])}</h3><p>{esc(x['a'])}</p>" for x in faq)
        ld.append({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": x["q"], "acceptedAnswer": {"@type": "Answer", "text": x["a"]}} for x in faq]})
    hero = f'<img src="{esc(p["image"])}" alt="{esc(p.get("image_alt", ""))}">' if p.get("image") else ""
    body = (f"<article><h1>{esc(p['title'])}</h1><div class='meta'>Published {p['date']}"
            + (f" &middot; Updated {p['updated']}" if p["updated"] != p["date"] else "")
            + f"</div>{hero}{p['body_html']}{faq_html}</article>"
            + f"<div class='box'><strong>Need a property condition assessment?</strong><br>"
              f"C and J Property Assessments serves investors, lenders and private equity funds across North Carolina, "
              f"Virginia and South Carolina. Expedited 24&ndash;48 hour report delivery is available for an additional fee &mdash; "
              f"call to order. <a href='{MAIN}'>Request a quote</a>.</div>")
    return page(p["title"], p["description"], url, body, ld, "article", p.get("image"))


def main():
    posts = load_posts()
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir()
    if STATIC.exists():
        shutil.copytree(STATIC, DIST / "static")
    for p in posts:
        (DIST / f"{p['slug']}.html").write_text(render_post(p), encoding="utf-8")
    cards = "".join(f"<a class='card' href='/{esc(p['slug'])}'><h2>{esc(p['title'])}</h2><p>{esc(p['description'])}</p></a>" for p in posts)
    (DIST / "index.html").write_text(page(
        f"{NAME} Blog | Commercial PCA & Due Diligence Insights",
        "Guides on property condition assessments, commercial inspections and capital reserves for investors and lenders in NC, VA and SC.",
        SITE + "/", f"<h1>Commercial property due diligence insights</h1><p class='meta'>Property condition assessments, inspections and capital planning for North Carolina, Virginia and South Carolina.</p>{cards}"), encoding="utf-8")
    today = datetime.date.today().isoformat()
    urls = [f"<url><loc>{SITE}/</loc><lastmod>{posts[0]['updated'] if posts else today}</lastmod></url>"] + [
        f"<url><loc>{SITE}/{p['slug']}</loc><lastmod>{p['updated']}</lastmod></url>" for p in posts]
    (DIST / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                                      + "".join(urls) + "</urlset>\n", encoding="utf-8")
    (DIST / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {SITE}/sitemap.xml\n", encoding="utf-8")
    llms = [f"# {NAME}", "",
            "> Commercial Property Condition Assessments (ASTM E2018), pre-contract inspections, routine commercial inspections, "
            "due-diligence inspections and capital needs assessments for real estate investors, lenders and private equity funds "
            "in North Carolina, Virginia and South Carolina, with nationwide travel available.", "",
            f"- Main site and quote requests: {MAIN}", "", "## Articles", ""]
    llms += [f"- [{p['title']}]({SITE}/{p['slug']}): {p['description']}" for p in posts]
    (DIST / "llms.txt").write_text("\n".join(llms) + "\n", encoding="utf-8")
    (DIST / "404.html").write_text(page("Page not found", "Page not found", SITE + "/", "<h1>Page not found</h1><p><a href='/'>Back to the blog</a></p>"), encoding="utf-8")
    print(f"built {len(posts)} posts -> {DIST}")


if __name__ == "__main__":
    main()
