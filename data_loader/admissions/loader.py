"""Validate and transactionally load a complete versioned admissions catalogue."""
import hashlib
import json
import sqlite3
from collections import Counter
from pathlib import Path


def validate(dataset, snapshot=None):
    if dataset.get("schema_version") != 1 or dataset.get("admission_year") != 2026:
        raise ValueError("Expected catalogue schema 1, admission year 2026")
    universities = {x["id"] for x in dataset["universities"]}
    if universities != {"hse", "itmo", "bmstu", "mipt", "mephi", "mai", "msal"}:
        raise ValueError("The catalogue must contain all seven universities")
    sources = {x["id"]: x for x in dataset["sources"]}
    if len(sources) != len(dataset["sources"]):
        raise ValueError("Duplicate source IDs")
    ids = set()
    counts = Counter()
    for row in dataset["rules"]:
        if row["id"] in ids:
            raise ValueError(f"Duplicate rule ID: {row['id']}")
        ids.add(row["id"])
        if row["admission_year"] != dataset["admission_year"]:
            raise ValueError("Mixed admission years")
        if row["university_id"] not in universities:
            raise ValueError("Unknown university")
        if row["source_id"] not in sources or sources[row["source_id"]]["university"] != row["university_id"]:
            raise ValueError("Source does not belong to rule's university")
        if not row["benefit_types"] or set(row["benefit_types"]) - {"bvi", "100_points"}:
            raise ValueError("Unknown benefit type")
        for key in ("olympiad_name", "olympiad_profile", "program_scope", "benefit"):
            if not row["values"].get(key):
                raise ValueError(f"Missing {key} in rule {row['id']}")
        if not ((row["location"].get("row") and row["location"].get("table")) or
                (row["location"].get("page") and row["location"].get("paragraph"))):
            raise ValueError("Missing source locator")
        counts[row["university_id"]] += 1
    if set(counts) != universities:
        raise ValueError("At least one university has no rules")
    if snapshot is not None:
        root = Path(snapshot).resolve()
        for source in sources.values():
            path = (root / source["file"]).resolve()
            if not path.is_relative_to(root):
                raise ValueError("Source path escapes the snapshot")
            if hashlib.sha256(path.read_bytes()).hexdigest() != source["sha256"]:
                raise ValueError(f"Source checksum mismatch: {source['id']}")
    return dict(sorted(counts.items()))


SCHEMA = """
CREATE TABLE IF NOT EXISTS admission_university (
    admission_year INTEGER NOT NULL, id TEXT NOT NULL, payload TEXT NOT NULL,
    PRIMARY KEY (admission_year, id)
);
CREATE TABLE IF NOT EXISTS admission_source (
    admission_year INTEGER NOT NULL, id TEXT NOT NULL, university_id TEXT NOT NULL,
    payload TEXT NOT NULL, PRIMARY KEY (admission_year, id),
    FOREIGN KEY (admission_year, university_id) REFERENCES admission_university(admission_year,id)
);
CREATE TABLE IF NOT EXISTS admission_rule (
    admission_year INTEGER NOT NULL, id TEXT NOT NULL, university_id TEXT NOT NULL,
    source_id TEXT NOT NULL, category TEXT NOT NULL, olympiad_name TEXT NOT NULL,
    olympiad_profile TEXT NOT NULL, program_scope TEXT NOT NULL, payload TEXT NOT NULL,
    PRIMARY KEY (admission_year, id),
    FOREIGN KEY (admission_year, university_id) REFERENCES admission_university(admission_year,id),
    FOREIGN KEY (admission_year, source_id) REFERENCES admission_source(admission_year,id)
);
CREATE INDEX IF NOT EXISTS admission_rule_university ON admission_rule(admission_year, university_id);
CREATE INDEX IF NOT EXISTS admission_rule_profile ON admission_rule(admission_year, olympiad_profile);
"""


def dumps(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def rows_for(dataset):
    year = dataset["admission_year"]
    return {
        "admission_university": [(year, x["id"], dumps(x)) for x in dataset["universities"]],
        "admission_source": [(year, x["id"], x["university"], dumps(x)) for x in dataset["sources"]],
        "admission_rule": [(year, x["id"], x["university_id"], x["source_id"], x["category"],
                            x["values"]["olympiad_name"], x["values"]["olympiad_profile"], x["values"]["program_scope"], dumps(x))
                           for x in dataset["rules"]],
    }


def load_sqlite(dataset, database):
    counts = validate(dataset)
    connection = sqlite3.connect(database)
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executescript(SCHEMA)
        with connection:
            for table in ("admission_rule", "admission_source", "admission_university"):
                connection.execute(f"DELETE FROM {table} WHERE admission_year = ?", (dataset["admission_year"],))
            for table, rows in rows_for(dataset).items():
                marks = ",".join("?" for _ in rows[0])
                connection.executemany(f"INSERT INTO {table} VALUES ({marks})", rows)
            check = dict(connection.execute("SELECT university_id, count(*) FROM admission_rule WHERE admission_year = ? GROUP BY university_id", (dataset["admission_year"],)))
            if check != counts:
                raise ValueError("Imported row counts do not match the catalogue")
    finally:
        connection.close()
    return counts


def postgres_sql(dataset):
    """Lossless import into isolated tables in the application's existing schema.

    No guessed IDs or lossy conversion into the legacy benefit table. Apply with
    psql --set ON_ERROR_STOP=1 --file admissions_2026.sql against the target DB.
    """
    validate(dataset)
    statements = ["BEGIN;", "CREATE SCHEMA IF NOT EXISTS olympguide;", "SET LOCAL search_path TO olympguide;", "SET LOCAL standard_conforming_strings = on;", SCHEMA]
    for table in ("admission_rule", "admission_source", "admission_university"):
        statements.append(f"DELETE FROM {table} WHERE admission_year = {dataset['admission_year']};")
    def literal(value):
        if isinstance(value, int):
            return str(value)
        if "\x00" in value:
            raise ValueError("NUL is not valid in PostgreSQL text")
        return "'" + value.replace("'", "''") + "'"
    for table, rows in rows_for(dataset).items():
        for start in range(0, len(rows), 100):
            values = ["(" + ",".join(literal(x) for x in row) + ")" for row in rows[start:start + 100]]
            statements.append(f"INSERT INTO {table} VALUES\n" + ",\n".join(values) + ";")
    statements.append("COMMIT;")
    return "\n".join(statements) + "\n"
