"""Collect the 2026 official documents, including per-program HSE appendices."""
import argparse
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin

from lxml import html
from .sources import SNAPSHOT, clean, save_source


def read_source(key):
    return json.loads((SNAPSHOT / "sources" / (key + ".json")).read_text(encoding="utf-8"))


def discover():
    jobs = []
    tree = html.fromstring((SNAPSHOT / "sources/hse.html").read_bytes())
    field = None
    programs = []
    for row in tree.xpath("//table[contains(@class, 'olympiad-table')]//tr"):
        cells = row.xpath("./td")
        if len(cells) == 1:
            match = re.search(r"\d{2}\.\d{2}\.\d{2}", clean(row.text_content()))
            if match:
                field = match.group()
        if len(cells) == 3 and cells[2].xpath(".//a[@href]"):
            name = clean(cells[1].text_content())
            link = cells[2].xpath(".//a[@href]")[0]
            url = urljoin("https://ba.hse.ru/bolimp", link.get("href"))
            key = "hse_" + url.rstrip("/").rsplit("/", 1)[-1]
            jobs.append((key, url, "hse", name))
            programs.append({"name": name, "field_code": field, "source_id": key})
    if not programs or any(not p["field_code"] for p in programs):
        raise ValueError("HSE program table is empty or a field code could not be determined")
    (SNAPSHOT / "hse_programs.json").write_text(json.dumps(programs, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    tree = html.fromstring((SNAPSHOT / "sources/bmstu.html").read_bytes())
    data = json.loads(tree.xpath("//script[@id='__NEXT_DATA__']/text()")[0])
    documents = data["props"]["initialState"]["documents"]["data"]["content"]["document-list"][0]["documents"]
    for doc in documents:
        if doc["title"].startswith("Приложение 5") and not doc["title"].startswith("Приложение 5.2"):
            jobs.append(("bmstu_" + str(doc["id"]), doc["url"], "bmstu", doc["title"]))

    for link in read_source("mai")["links"]:
        if link["text"] == "Перечень олимпиад школьников":
            jobs.append(("mai_olympiads", link["url"], "mai", "Приложение 7. Перечень олимпиад школьников, 2026"))
    return jobs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    jobs = discover()
    (SNAPSHOT / "download_manifest.json").write_text(json.dumps(jobs, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    pending = [job for job in jobs if args.refresh or not (SNAPSHOT / "sources" / (job[0] + ".json")).exists()]
    failures = []
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(save_source, *job): job[0] for job in pending}
        for future in as_completed(futures):
            key = futures[future]
            try:
                record = future.result()
                print(key, len(record.get("pages", [])), "pages", flush=True)
            except Exception as error:
                failures.append((key, str(error)))
                print(key, type(error).__name__, str(error), flush=True)
    if failures:
        raise SystemExit(f"Failed sources: {failures}")
    print(f"Ready: {len(jobs)} documents")


if __name__ == "__main__":
    main()
