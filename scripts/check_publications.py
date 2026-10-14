#!/usr/bin/env python3
"""
Weekly publication check for the CV site.

Reads the works on an ORCID record, finds any that are not yet on index.html
(matched by DOI, then by title), looks up full details on Crossref, formats
them in the site's house style and inserts them at the top of the right
section. It also writes a pull-request description for review.

Nothing is published automatically: the GitHub workflow opens a pull request
and the page only changes when that pull request is merged.

Standard library only, so the workflow needs no installs.

Usage:
    python scripts/check_publications.py --html index.html \
        --orcid 0009-0000-7462-3217 --pr-body pr_body.md

For testing without network access, set FIXTURE_DIR to a folder of saved
responses (works.json, work-<put-code>.json, crossref-<doi>.json).
"""
import argparse
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ME_FAMILY = "lodh"
USER_AGENT = "ekarsi-cv-publication-check/1.0 (+https://github.com/ekarsilodh/ekarsi-cv)"
MONTHS = ["Jan.", "Feb.", "Mar.", "Apr.", "May", "Jun.", "Jul.", "Aug.", "Sep.", "Oct.", "Nov.", "Dec."]

# ORCID work type -> section on the page (data-type of the .pub-group)
ORCID_TYPES = {
    "journal-article": "journal",
    "conference-paper": "conference",
    "conference-proceedings": "conference",
    "book-chapter": "chapter",
    "preprint": "preprint",
    "working-paper": "preprint",
}
# Crossref type -> section, used when ORCID says "other" or is missing
CROSSREF_TYPES = {
    "journal-article": "journal",
    "proceedings-article": "conference",
    "book-chapter": "chapter",
    "posted-content": "preprint",
}
SECTION_NAMES = {"journal": "Journal articles", "conference": "Conference papers",
                 "preprint": "Preprints", "chapter": "Book chapters"}


# --------------------------------------------------------------------------- fetching
def get_json(url):
    fixtures = os.environ.get("FIXTURE_DIR")
    if fixtures:
        return json.load(open(os.path.join(fixtures, fixture_name(url))))
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": USER_AGENT})
    last = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                raise
            last = e
        except (urllib.error.URLError, TimeoutError) as e:
            last = e
        time.sleep(2 * (attempt + 1))
    raise last


def fixture_name(url):
    if "api.crossref.org" in url:
        doi = urllib.parse.unquote(url.rsplit("/works/", 1)[1])
        return "crossref-" + re.sub(r"[^a-z0-9]+", "_", doi.lower()) + ".json"
    m = re.search(r"/work/(\d+)$", url)
    if m:
        return "work-%s.json" % m.group(1)
    return "works.json"


# --------------------------------------------------------------------------- helpers
def norm_title(t):
    return re.sub(r"[^a-z0-9]+", "", html.unescape(re.sub(r"<[^>]+>", "", t or "")).lower())


def norm_doi(d):
    d = (d or "").strip().lower()
    d = re.sub(r"^https?://(dx\.)?doi\.org/", "", d)
    return re.sub(r"^doi:\s*", "", d)


def val(obj, *path):
    """Safely walk nested ORCID JSON like {"title": {"title": {"value": "..."}}}."""
    for p in path:
        if obj is None:
            return None
        obj = obj.get(p) if isinstance(obj, dict) else None
    return obj


def initials(given):
    parts = re.split(r"\s+", given.strip())
    out = []
    for p in parts:
        if not p:
            continue
        if "-" in p.strip("-"):
            out.append("-".join(s[0].upper() + "." for s in p.split("-") if s))
        else:
            out.append(p[0].upper() + ".")
    return " ".join(out)


def format_author(given, family):
    family = (family or "").strip()
    given = (given or "").strip()
    name = (initials(given) + " " + family).strip() if given else family
    is_me = family.lower() == ME_FAMILY
    return name, is_me


def join_authors(names):
    """House style: 'A, B, and C' / 'A and B' / 'A'. Own name underlined."""
    parts = [('<span class="me">%s</span>' % html.escape(n)) if me else html.escape(n) for n, me in names]
    if len(parts) <= 1:
        return "".join(parts)
    if len(parts) == 2:
        return parts[0] + " and " + parts[1]
    return ", ".join(parts[:-1]) + ", and " + parts[-1]


def pages_text(page, article_number):
    if page:
        page = page.replace("--", "-")
        if "-" in page:
            a, b = page.split("-", 1)
            return "pp. %s–%s" % (a.strip(), b.strip())
        return "p. %s" % page
    if article_number:
        return "p. %s" % article_number
    return ""


def month_year(year, month):
    if not year:
        return ""
    try:
        m = int(month) if month else 0
    except ValueError:
        m = 0
    return ("%s %s" % (MONTHS[m - 1], year)) if 1 <= m <= 12 else str(year)


# --------------------------------------------------------------------------- reading the page
def existing_on_page(page):
    dois = set(norm_doi(d) for d in re.findall(r'<span class="doi">doi:([^<]+)</span>', page))
    dois |= set(norm_doi(d) for d in re.findall(r'href="https?://(?:dx\.)?doi\.org/([^"]+)"', page))
    titles = set(norm_title(t) for t in re.findall(r'<p class="pub-title">(.*?)</p>', page, flags=re.S))
    ids = set(re.findall(r'\sid="([^"]+)"', page))
    return dois, titles, ids


# --------------------------------------------------------------------------- ORCID + Crossref
def orcid_works(orcid):
    data = get_json("https://pub.orcid.org/v3.0/%s/works" % orcid)
    works = []
    for group in data.get("group") or []:
        summaries = group.get("work-summary") or []
        if not summaries:
            continue
        s = summaries[0]          # ORCID lists the preferred version first
        ext = (val(group, "external-ids", "external-id") or []) + (val(s, "external-ids", "external-id") or [])
        doi = ""
        for e in ext:
            if (e.get("external-id-type") or "").lower() == "doi" and (e.get("external-id-relationship") or "self") == "self":
                doi = norm_doi(e.get("external-id-value"))
                break
        works.append({
            "put_code": s.get("put-code"),
            "title": val(s, "title", "title", "value") or "",
            "type": (s.get("type") or "").lower(),
            "year": val(s, "publication-date", "year", "value"),
            "month": val(s, "publication-date", "month", "value"),
            "journal": val(s, "journal-title", "value") or "",
            "doi": doi,
        })
    return works


def crossref(doi):
    try:
        return get_json("https://api.crossref.org/works/" + urllib.parse.quote(doi, safe="/:;()"))["message"]
    except Exception as e:  # missing or unreachable: fall back to ORCID's own details
        print("  Crossref lookup failed for %s (%s); using ORCID details" % (doi, e), file=sys.stderr)
        return None


def orcid_contributors(orcid, put_code):
    try:
        w = get_json("https://pub.orcid.org/v3.0/%s/work/%s" % (orcid, put_code))
    except Exception:
        return []
    out = []
    for c in val(w, "contributors", "contributor") or []:
        name = (val(c, "credit-name", "value") or "").strip()
        if not name:
            continue
        bits = name.split()
        out.append(format_author(" ".join(bits[:-1]), bits[-1]))
    return out


def build_entry(w, cr, contributors, used_ids):
    """Return (section, html_li, info_for_pr) in the site's house style."""
    section = ORCID_TYPES.get(w["type"]) or (CROSSREF_TYPES.get(cr.get("type")) if cr else None)
    title = (cr.get("title") or [w["title"]])[0] if cr else w["title"]
    title = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", title or "")).strip()

    authors = []
    if cr and cr.get("author"):
        for a in cr["author"]:
            if a.get("family") or a.get("given"):
                authors.append(format_author(a.get("given"), a.get("family") or a.get("given")))
            elif a.get("name"):
                authors.append((a["name"], False))
    elif contributors:
        authors = contributors
    first = bool(authors) and authors[0][1]
    needs_authors = not authors
    author_html = join_authors(authors) if authors else \
        '<span class="me">E. Lodh</span> <span class="small">(full author list to be added)</span>'

    year = w["year"]
    month = w["month"]
    if cr:
        dp = (val(cr, "published", "date-parts") or val(cr, "issued", "date-parts") or [[None]])[0]
        year = year or (str(dp[0]) if dp and dp[0] else None)
        month = month or (dp[1] if len(dp) > 1 else None)
    container = ((cr.get("container-title") or [""])[0] if cr else "") or w["journal"]
    container = html.unescape(container)

    bits = []
    if section == "journal":
        bits.append("<i>%s</i>" % html.escape(container or "Journal"))
        if cr and cr.get("volume"): bits.append("vol. %s" % html.escape(cr["volume"]))
        if cr and cr.get("issue"): bits.append("no. %s" % html.escape(cr["issue"]))
        pt = pages_text(cr.get("page") if cr else None, cr.get("article-number") if cr else None)
        if pt: bits.append(html.escape(pt))
        my = month_year(year, month)
        if my: bits.append(my)
    elif section == "conference":
        bits.append("<i>%s</i>" % html.escape(container or "Conference proceedings"))
        if year: bits.append(str(year))
        pt = pages_text(cr.get("page") if cr else None, None)
        if pt: bits.append(html.escape(pt))
    elif section == "preprint":
        server = ""
        if cr:
            inst = cr.get("institution") or []
            server = (inst[0].get("name") if inst and isinstance(inst[0], dict) else "") or (cr.get("publisher") or "")
        bits.append("<i>%s</i>" % html.escape(server or container or "Preprint"))
        my = month_year(year, month)
        if my: bits.append(my)
    else:  # chapter
        bits.append("In <i>%s</i>" % html.escape(container or "edited volume"))
        if cr and cr.get("publisher"): bits.append(html.escape(cr["publisher"]))
        if year: bits.append(str(year))
    venue = ", ".join(bits) + "."

    doi = w["doi"]
    base = "pub-" + (re.sub(r"[^a-z0-9]+", "-", doi.split("/", 1)[-1]).strip("-") if doi else re.sub(r"[^a-z0-9]+", "-", title.lower())[:40].strip("-"))
    pid, n = base, 2
    while pid in used_ids:
        pid, n = "%s-%d" % (base, n), n + 1
    used_ids.add(pid)

    title_html = ('<a href="https://doi.org/%s" target="_blank" rel="noopener">%s</a>' % (html.escape(doi, quote=True), html.escape(title))) if doi else html.escape(title)
    meta = []
    if doi: meta.append('<span class="doi">doi:%s</span>' % html.escape(doi))
    if first: meta.append('<span class="flag">First author</span>')
    meta_html = ('\n            <p class="pub-meta">%s</p>' % "".join(meta)) if meta else ""

    li = ('        <li class="pub" data-first="%s" id="%s" data-themes="">\n'
          '          <span class="pub-n">[0]</span>\n'
          '          <div>\n'
          '            <p class="pub-title">%s</p>\n'
          '            <p class="pub-authors">%s</p>\n'
          '            <p class="pub-venue">%s</p>%s\n'
          '          </div>\n'
          '          <span class="pub-year">%s</span>\n'
          '        </li>\n') % ("true" if first else "false", pid, title_html, author_html, venue, meta_html, html.escape(str(year or "")))
    info = {"title": title, "section": section, "venue": re.sub(r"<[^>]+>", "", venue), "doi": doi,
            "first": first, "needs_authors": needs_authors, "id": pid}
    return section, li, info


# --------------------------------------------------------------------------- writing the page
def insert_and_renumber(page, section, li):
    m = re.search(r'<div class="pub-group" data-type="%s">.*?<ol class="pubs">\n' % section, page, flags=re.S)
    if not m:
        return page, False
    return page[:m.end()] + li + page[m.end():], True


def renumber(page):
    def fix_group(m):
        k = [0]
        def num(_):
            k[0] += 1
            return '<span class="pub-n">[%d]</span>' % k[0]
        return re.sub(r'<span class="pub-n">\[\d+\]</span>', num, m.group(0))
    return re.sub(r'<div class="pub-group" data-type="[a-z]+">.*?</ol>', fix_group, page, flags=re.S)


def write_output(name, value):
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a") as f:
            f.write("%s=%s\n" % (name, value))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", default="index.html")
    ap.add_argument("--orcid", required=True)
    ap.add_argument("--pr-body", default="pr_body.md")
    args = ap.parse_args()

    page = open(args.html, encoding="utf-8").read()
    dois, titles, used_ids = existing_on_page(page)
    works = orcid_works(args.orcid)
    print("ORCID lists %d works; the page has %d DOIs." % (len(works), len(dois)))

    added, skipped, unplaced = [], [], []
    seen = set()
    for w in works:
        key = w["doi"] or norm_title(w["title"])
        if not key or key in seen:
            continue
        seen.add(key)
        if (w["doi"] and w["doi"] in dois) or norm_title(w["title"]) in titles:
            continue                                    # already on the page
        cr = crossref(w["doi"]) if w["doi"] else None
        section = ORCID_TYPES.get(w["type"]) or (CROSSREF_TYPES.get(cr.get("type")) if cr else None)
        if not section:
            skipped.append(w)                           # e.g. posters, datasets, theses
            continue
        contributors = [] if (cr and cr.get("author")) else orcid_contributors(args.orcid, w["put_code"])
        section, li, info = build_entry(w, cr, contributors, used_ids)
        page, ok = insert_and_renumber(page, section, li)
        (added if ok else unplaced).append(info)
        print("  New: [%s] %s" % (section, info["title"]))

    write_output("new_count", str(len(added)))
    if not added:
        print("Nothing new to add.")
        return 0

    page = renumber(page)
    open(args.html, "w", encoding="utf-8").write(page)

    lines = ["The weekly check found **%d publication%s on ORCID** that %s not on the website yet. "
             "They have been added in the house style; please review them before merging." %
             (len(added), "" if len(added) == 1 else "s", "is" if len(added) == 1 else "are"), "", "### Added", ""]
    for a in added:
        lines.append("- **%s**  \n  %s — %s%s%s" % (a["title"], SECTION_NAMES[a["section"]], a["venue"],
                     ("  \n  DOI: https://doi.org/" + a["doi"]) if a["doi"] else "",
                     "  \n  Marked as first-authored." if a["first"] else ""))
    lines += ["", "### Before merging", "",
              "- [ ] Check titles, author names and venue details (Crossref data is sometimes incomplete).",
              "- [ ] Author names must match the spelling used elsewhere on the page (e.g. `S. Majumder`), or the co-author network will show the same person twice.",
              "- [ ] Add a topic so the paper appears in the topic filter: set `data-themes` to one of "
              "`epigenomics`, `clinical`, `signalling`, `binding`, `algorithms`."]
    if any(a["first"] for a in added):
        lines.append("- [ ] A first-authored paper was added: update the sentence near the top that says how many papers you are first author of.")
    if any(a["needs_authors"] for a in added):
        lines.append("- [ ] Some entries had no author list on Crossref or ORCID; complete them (marked *full author list to be added*).")
    if any(a["section"] == "journal" for a in added) and "data-type=\"preprint\"" in page:
        lines.append("- [ ] If one of these is the published version of your preprint, consider removing or updating the preprint entry.")
    if skipped:
        lines += ["", "### Not added (types the page doesn't list)", ""]
        lines += ["- %s (%s)" % (w["title"], w["type"] or "unknown type") for w in skipped]
    if unplaced:
        lines += ["", "### Could not place", ""]
        lines += ["- %s: no `%s` section found on the page" % (a["title"], a["section"]) for a in unplaced]
    lines += ["", "_Source: ORCID record %s, with details from Crossref._" % args.orcid]
    open(args.pr_body, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print("Added %d; wrote %s and %s." % (len(added), args.html, args.pr_body))
    return 0


if __name__ == "__main__":
    sys.exit(main())
