"""Re-download pinned official sources into a separate review directory."""
import argparse
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from .paths import ROOT, SNAPSHOT
from .sources import save_source


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=SNAPSHOT / "source_manifest.json")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--university", choices=("hse", "itmo", "bmstu", "mipt", "mephi", "mai", "msal"))
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    if args.output.resolve().is_relative_to((ROOT / "snapshots").resolve()):
        parser.error("Download into a review directory, not over committed snapshots")
    if not 1 <= args.workers <= 8:
        parser.error("--workers must be between 1 and 8")
    sources = json.loads(args.manifest.read_text(encoding="utf-8"))
    if args.university:
        sources = [x for x in sources if x["university"] == args.university]
    report = []
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        jobs = {executor.submit(save_source, x["id"], x["url"], x["university"], x.get("title"), args.output): x for x in sources}
        for future in as_completed(jobs):
            old = jobs[future]
            try:
                new = future.result()
                status = "unchanged" if new["sha256"] == old["sha256"] else "changed"
                report.append({"id": old["id"], "status": status, "old_sha256": old["sha256"], "new_sha256": new["sha256"]})
            except Exception as error:
                report.append({"id": old["id"], "status": "failed", "error": str(error)})
            print(old["id"], report[-1]["status"], flush=True)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "fetch_report.json").write_text(json.dumps(sorted(report, key=lambda x: x["id"]), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if any(x["status"] == "failed" for x in report):
        raise SystemExit("Some sources failed; see fetch_report.json. The committed snapshot is unchanged.")


if __name__ == "__main__":
    main()
