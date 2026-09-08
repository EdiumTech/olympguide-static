"""Re-extract cached PDFs offline after a parser change."""
import json
from concurrent.futures import ThreadPoolExecutor
from .sources import SNAPSHOT, extract_pdf

def process(path):
    record = json.loads(path.read_text(encoding="utf-8"))
    if "pages" in record:
        record["pages"] = extract_pdf(SNAPSHOT / record["file"])
        path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(record["id"], flush=True)

if __name__ == "__main__":
    with ThreadPoolExecutor(max_workers=4) as executor:
        list(executor.map(process, sorted((SNAPSHOT / "sources").glob("*.json"))))
