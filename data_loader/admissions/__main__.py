"""Offline catalogue validation, search, SQLite loading and PostgreSQL export."""
import argparse
import json
from pathlib import Path
from .loader import load_sqlite, postgres_sql, validate
from .paths import SNAPSHOT


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=SNAPSHOT / "catalog.json")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("validate")
    commands.add_parser("build")
    download = commands.add_parser("download", help="Download the verified 2026 release snapshot")
    download.add_argument("--archive", type=Path, help="Use a previously downloaded ZIP")
    download.add_argument("--output", type=Path, default=SNAPSHOT)
    load = commands.add_parser("load")
    load.add_argument("--database", required=True, type=Path)
    sql = commands.add_parser("export-sql")
    sql.add_argument("--output", required=True, type=Path)
    query = commands.add_parser("search")
    query.add_argument("--university", choices=("hse", "itmo", "bmstu", "mipt", "mephi", "mai", "msal"))
    query.add_argument("--text", default="")
    query.add_argument("--benefit", choices=("bvi", "100_points"))
    query.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()
    if args.command == "download":
        from .download import install
        try:
            destination = install(target=args.output, archive=args.archive)
        except (ValueError, OSError) as error:
            parser.exit(1, f"Download failed: {error}\n")
        print(f"Verified snapshot: {destination}")
        return
    if args.command == "build":
        from .normalize import build
        build()
        return
    if not args.catalog.is_file():
        parser.exit(1, "Dataset is not installed. Run: python -m admissions download\n")
    dataset = json.loads(args.catalog.read_text(encoding="utf-8"))
    counts = validate(dataset, args.catalog.parent)
    if args.command == "validate":
        print(json.dumps({"admission_year": dataset["admission_year"], "rules": counts, "total": sum(counts.values()), "sources": len(dataset["sources"])}, ensure_ascii=False, indent=2))
    elif args.command == "load":
        load_sqlite(dataset, args.database)
        print(f"Loaded {sum(counts.values())} rules into {args.database}")
    elif args.command == "export-sql":
        args.output.write_text(postgres_sql(dataset), encoding="utf-8")
        print(f"SQL written to {args.output}")
    elif args.command == "search":
        matches = [row for row in dataset["rules"]
                   if (not args.university or row["university_id"] == args.university)
                   and (not args.benefit or args.benefit in row["benefit_types"])
                   and args.text.casefold() in json.dumps(row["values"], ensure_ascii=False).casefold()]
        print(json.dumps({"total": len(matches), "rules": matches[:max(0, args.limit)]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
