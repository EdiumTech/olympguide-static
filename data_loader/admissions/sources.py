"""Download and preserve official sources before interpreting admission rules."""
import hashlib
import json
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, quote

from lxml import html
import pdfplumber

from .paths import ROOT, SNAPSHOT


def clean(value):
    return re.sub(r"\s+", " ", (value or "").replace("\xad", "")).strip()


def extract_pdf(path):
    pages = []
    with pdfplumber.open(path) as document:
        for n, page in enumerate(document.pages, 1):
            # Close cells which continue past a page break. Without this, pdfplumber
            # silently drops their text (e.g. Moscow Olympiad in HSE Mathematics).
            tables = page.find_tables()
            boundaries = sorted({coordinate for table in tables for coordinate in (table.bbox[1], table.bbox[3])})
            # An entire final row can be open at the page boundary and therefore
            # absent from find_tables(), not just a merged cell within a table.
            for table in tables:
                bottoms = [edge["bottom"] for edge in page.edges if edge["orientation"] == "v"
                           and edge["bottom"] - edge["top"] > 3
                           and table.bbox[0] - 1 <= edge["x0"] <= table.bbox[2] + 1
                           and edge["top"] >= table.bbox[1] - 1]
                if bottoms:
                    boundaries.append(max(bottoms))
            settings = {"explicit_horizontal_lines": boundaries} if boundaries else {}
            if path.stem == "itmo_vsosh":
                settings.update(vertical_strategy="explicit", explicit_vertical_lines=[35.76, 425.28, 552.48])
            if path.stem in ("mephi_vsosh_bvi", "mephi_vsosh_100"):
                settings.update(vertical_strategy="explicit", explicit_vertical_lines=[66.704, 211.5785, 545.42])
            closed_tables = page.find_tables(settings)
            table_years = []
            for table in closed_tables:
                context = page.crop((0, 0, page.width, max(1, table.bbox[1]))).extract_text() or ""
                years = re.findall(r"уровней\s+на\s+(20\d{2}/\d{2})", context)
                table_years.append(years[-1] if years else None)
            pages.append({"page": n, "text": page.extract_text() or "", "tables": [t.extract() for t in closed_tables], "table_years": table_years})
    return pages


def save_source(key, url, university, title=None, snapshot=SNAPSHOT):
    if not re.fullmatch(r"[a-z0-9_]+", key):
        raise ValueError("Source ID must contain only lowercase letters, digits and underscores")
    snapshot = Path(snapshot)
    request = urllib.request.Request(quote(url, safe=":/?=&%+#"), headers={"User-Agent": "OlympGuide/1.0 (admission rules research)"})
    with urllib.request.urlopen(request, timeout=60) as response:
        body = response.read()
        resolved_url = response.url
    is_pdf = body.startswith(b"%PDF")
    directory = snapshot / "sources"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / (key + (".pdf" if is_pdf else ".html"))
    path.write_bytes(body)
    record = {
        "id": key, "university": university, "url": url, "resolved_url": resolved_url,
        "title": title, "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "sha256": hashlib.sha256(body).hexdigest(), "file": path.relative_to(snapshot).as_posix(),
    }
    if is_pdf:
        record["pages"] = extract_pdf(path)
    else:
        tree = html.fromstring(body)
        for node in tree.xpath("//script|//style|//noscript"):
            node.drop_tree()
        record["title"] = title or clean(" ".join(tree.xpath("//title/text()")))
        record["text"] = clean(tree.text_content())
        record["links"] = [
            {"text": clean(a.text_content()), "url": urljoin(resolved_url, a.get("href"))}
            for a in tree.xpath("//a[@href]")
        ]
        record["tables"] = [
            [[{"text": clean(cell.text_content()), "rowspan": int(cell.get("rowspan", 1)),
               "colspan": int(cell.get("colspan", 1))} for cell in row.xpath("./th|./td")]
             for row in table.xpath(".//tr")]
            for table in tree.xpath("//table")
        ]
    (directory / (key + ".json")).write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return record


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("key")
    parser.add_argument("url")
    parser.add_argument("university")
    args = parser.parse_args()
    result = save_source(args.key, args.url, args.university)
    print(json.dumps({k: v for k, v in result.items() if k not in ("text", "pages", "tables", "links")}, ensure_ascii=False))
    if "links" in result:
        for link in result["links"]:
            if re.search(r"олимп|бви|особ|2026|правил|прилож", link["text"], re.I):
                print(link["text"], link["url"])
