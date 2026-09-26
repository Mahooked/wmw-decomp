#!/usr/bin/env python3
"""Dump the schema of the game's SQLite databases.

The level/meta data ships as three SQLite files under assets/Data. This tool
records their structure -- tables, columns, types, constraints, indexes, and
row counts -- so the format is documented without redistributing the data
itself. No row *contents* are emitted; only schema and aggregate counts.

Usage:
    python tools/dbschema.py <db> [<db> ...] [--out out/db]
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

# Objects whose names we record but whose SQL we do not need to interpret.
_ORDER = {"table": 0, "view": 1, "index": 2, "trigger": 3}


def ro_uri(path: Path) -> str:
    # Read-only so a stray query can never modify the shipped database.
    return "file:%s?mode=ro" % path.resolve().as_posix().replace("?", "%3f")


def connect(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(ro_uri(path), uri=True)


def header_facts(con: sqlite3.Connection) -> dict:
    """Facts straight from the SQLite header, independent of the schema."""
    page_size = con.execute("PRAGMA page_size").fetchone()[0]
    return {
        "page_size": page_size,
        "encoding": con.execute("PRAGMA encoding").fetchone()[0],
        "journal_mode": con.execute("PRAGMA journal_mode").fetchone()[0],
        "freelist_pages": con.execute("PRAGMA freelist_count").fetchone()[0],
        "schema_format": con.execute("PRAGMA schema_version").fetchone()[0],
        "application_id": con.execute("PRAGMA application_id").fetchone()[0],
        "user_version": con.execute("PRAGMA user_version").fetchone()[0],
    }


def objects(con: sqlite3.Connection) -> list[dict]:
    rows = con.execute(
        "SELECT type, name, tbl_name, sql FROM sqlite_master"
        " WHERE sql IS NOT NULL ORDER BY type, name"
    ).fetchall()
    out = []
    for typ, name, tbl, sql in rows:
        out.append(
            {
                "type": typ,
                "name": name,
                "table": tbl,
                "sql": " ".join(sql.split()),
            }
        )
    out.sort(key=lambda d: (_ORDER.get(d["type"], 9), d["name"]))
    return out


def columns(con: sqlite3.Connection, table: str) -> list[dict]:
    # PRAGMA table_info gives name/type/notnull/default/pk, which is enough to
    # describe the shape without interpreting the CREATE TABLE text.
    info = con.execute('PRAGMA table_info("%s")' % table.replace('"', '""')).fetchall()
    return [
        {
            "name": r[1],
            "type": r[2] or "(none)",
            "notnull": bool(r[3]),
            "default": r[4],
            "pk": r[5],
        }
        for r in info
    ]


def row_count(con: sqlite3.Connection, table: str) -> int | None:
    # Some tables are virtual or absent; a failure here is not fatal.
    try:
        return con.execute(
            'SELECT count(*) FROM "%s"' % table.replace('"', '""')
        ).fetchone()[0]
    except sqlite3.Error:
        return None


def foreign_keys(con: sqlite3.Connection, table: str) -> list[dict]:
    try:
        rows = con.execute('PRAGMA foreign_key_list("%s")' % table).fetchall()
    except sqlite3.Error:
        return []
    return [
        {"from": r[3], "table": r[2], "to": r[4] or r[3], "on_update": r[5], "on_delete": r[6]}
        for r in rows
    ]


def analyse(path: Path) -> dict:
    con = connect(path)
    try:
        objs = objects(con)
        tables = [o for o in objs if o["type"] == "table"]
        for t in tables:
            t["columns"] = columns(con, t["name"])
            t["rows"] = row_count(con, t["name"])
            t["foreign_keys"] = foreign_keys(con, t["name"])
        indexes = [o for o in objs if o["type"] == "index"]
        for i in indexes:
            # SQLite auto-generates sql=NULL for indexes on UNIQUE constraints;
            # those are already excluded above, so everything here is explicit.
            i["columns"] = [
                r[2]
                for r in con.execute('PRAGMA index_info("%s")' % i["name"]).fetchall()
            ]
        return {
            "file": path.name,
            "bytes": path.stat().st_size,
            "header": header_facts(con),
            "tables": tables,
            "views": [o for o in objs if o["type"] == "view"],
            "indexes": indexes,
            "triggers": [o for o in objs if o["type"] == "trigger"],
        }
    finally:
        con.close()


def render(db: dict) -> str:
    L: list[str] = []
    L.append("# %s (%d bytes)" % (db["file"], db["bytes"]))
    h = db["header"]
    L.append(
        "# page_size=%(page_size)d encoding=%(encoding)s journal=%(journal_mode)s"
        " freelist=%(freelist_pages)d user_version=%(user_version)d"
        " app_id=%(application_id)d" % h
    )
    L.append("")
    L.append("Tables: %d   views: %d   indexes: %d   triggers: %d"
             % (len(db["tables"]), len(db["views"]), len(db["indexes"]),
                len(db["triggers"])))
    L.append("")
    for t in db["tables"]:
        L.append("## %s%s" % (t["name"], "" if t["rows"] is None else "  (%d rows)" % t["rows"]))
        L.append("")
        L.append("    %s" % t["sql"])
        L.append("")
        for c in t["columns"]:
            bits = [c["type"]]
            if c["pk"]:
                bits.append("PRIMARY KEY" if c["pk"] == 1 else "pk=%d" % c["pk"])
            if c["notnull"]:
                bits.append("NOT NULL")
            if c["default"] is not None:
                bits.append("DEFAULT %s" % c["default"])
            L.append("      %-28s %s" % (c["name"], ", ".join(bits)))
        for fk in t["foreign_keys"]:
            L.append(
                "      FK %s -> %s(%s) on_update=%s on_delete=%s"
                % (fk["from"], fk["table"], fk["to"], fk["on_update"], fk["on_delete"])
            )
        L.append("")
    for i in db["indexes"]:
        L.append("INDEX %s on %s(%s)" % (i["name"], i["table"], ", ".join(i["columns"])))
    for v in db["views"]:
        L.append("VIEW %s" % v["name"])
    for g in db["triggers"]:
        L.append("TRIGGER %s" % g["name"])
    return "\n".join(L) + "\n"


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("dbs", nargs="+")
    ap.add_argument("--out", default="out/db")
    args = ap.parse_args(argv[1:])

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    reports = []
    for name in args.dbs:
        p = Path(name)
        if not p.is_file():
            print("dbschema: no such file: %s" % p, file=sys.stderr)
            return 1
        try:
            db = analyse(p)
        except sqlite3.DatabaseError as exc:
            print("dbschema: %s: %s" % (p, exc), file=sys.stderr)
            return 1
        reports.append(db)
        (out / (p.stem + ".schema.md")).write_text(render(db), encoding="utf-8", newline="\n")
        n = len(db["tables"])
        total = sum(t["rows"] or 0 for t in db["tables"])
        print(
            "dbschema: %s: %d tables, %d views, %d indexes, %d rows total"
            % (p.name, n, len(db["views"]), len(db["indexes"]), total)
        )

    (out / "schema.json").write_text(
        json.dumps(reports, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print("dbschema: wrote %s" % out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
