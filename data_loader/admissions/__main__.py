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
    if args.command == "build":
        from .normalize import build
        build()
        return
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
