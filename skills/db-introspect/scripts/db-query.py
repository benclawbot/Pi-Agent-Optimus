# /// script
# requires-python = ">=3.10"
# dependencies = ["psycopg2-binary", "pymysql", "db-to-sql"]
# ///

"""
Database Introspection

Query database schemas without running the app.
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Optional

# Detection patterns for connection strings
CONN_PATTERNS = {
    "postgres": ["DATABASE_URL", "POSTGRES_URL", "pg-connection"],
    "mysql": ["MYSQL_URL", "MYSQL_URL"],
    "sqlite": ["DATABASE_URL"],
    "sqlserver": ["MSSQL_URL", "SQLSERVER_URL"]
}


def detect_connection(project_root: str = ".") -> Optional[dict]:
    """Detect database connection from project files."""
    root = Path(project_root)

    # Check .env
    env_file = root / ".env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                if line.startswith("DATABASE_URL="):
                    url = line.split("=", 1)[1].strip()
                    if url.startswith("postgres"):
                        return {"db": "postgres", "conn": url}
                    elif url.startswith("mysql"):
                        return {"db": "mysql", "conn": url}
                    elif url.startswith("sqlite"):
                        return {"db": "sqlite", "conn": url}

    # Check package.json
    pkg_file = root / "package.json"
    if pkg_file.exists():
        import json
        try:
            with open(pkg_file) as f:
                pkg = json.load(f)
            conn = pkg.get("pg-connection") or pkg.get("database", {}).get("connection")
            if conn:
                return {"db": "postgres", "conn": conn}
        except Exception:
            pass

    # Check docker-compose
    dc_file = root / "docker-compose.yml"
    if dc_file.exists():
        with open(dc_file) as f:
            content = f.read()
            if "postgres" in content.lower():
                return {"db": "postgres", "conn": "postgresql://postgres:postgres@localhost:5432/postgres"}
            elif "mysql" in content.lower():
                return {"db": "mysql", "conn": "mysql://root:root@localhost:3306/mysql"}

    return None


def query_postgres(conn: str, query: str) -> list[dict]:
    """Query PostgreSQL database."""
    try:
        import psycopg2
        conn_obj = psycopg2.connect(conn)
        cur = conn_obj.cursor()
        cur.execute(query)
        
        if cur.description:
            columns = [desc[0] for desc in cur.description]
            rows = [dict(zip(columns, row)) for row in cur.fetchall()]
        else:
            rows = []
        
        cur.close()
        conn_obj.close()
        return rows
    except ImportError:
        return [{"error": "psycopg2 not installed"}]


def query_mysql(conn: str, query: str) -> list[dict]:
    """Query MySQL database."""
    try:
        import pymysql
        # Parse connection string
        conn_obj = pymysql.connect(host="localhost", user="root", password="", database="")
        cur = conn_obj.cursor()
        cur.execute(query)
        rows = [dict(zip([d[0] for d in cur.description], row)) for row in cur.fetchall()]
        cur.close()
        conn_obj.close()
        return rows
    except ImportError:
        return [{"error": "pymysql not installed"}]


def query_sqlite(conn: str, query: str) -> list[dict]:
    """Query SQLite database."""
    import sqlite3
    conn_obj = sqlite3.connect(conn.replace("sqlite://", ""))
    conn_obj.row_factory = sqlite3.Row
    cur = conn_obj.cursor()
    cur.execute(query)
    rows = [dict(row) for row in cur.fetchall()]
    conn_obj.close()
    return rows


def list_tables(db: str, conn: str) -> list[str]:
    """List all tables in database."""
    if db == "postgres":
        rows = query_postgres(conn, """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        return [r["table_name"] for r in rows]
    
    elif db == "mysql":
        rows = query_mysql(conn, "SHOW TABLES")
        return list(rows[0].values()) if rows else []
    
    elif db == "sqlite":
        rows = query_sqlite(conn, "SELECT name FROM sqlite_master WHERE type='table'")
        return [r["name"] for r in rows]
    
    return []


def get_schema(db: str, conn: str, table: str) -> dict:
    """Get table schema."""
    if db == "postgres":
        columns = query_postgres(conn, f"""
            SELECT 
                column_name, data_type, is_nullable, column_default,
                CASE WHEN pk.column_name IS NOT NULL THEN true ELSE false END as is_primary
            FROM information_schema.columns c
            LEFT JOIN (
                SELECT kcu.column_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                    ON tc.constraint_name = kcu.constraint_name
                WHERE tc.table_name = '{table}' AND tc.constraint_type = 'PRIMARY KEY'
            ) pk ON c.column_name = pk.column_name
            WHERE c.table_name = '{table}'
            ORDER BY ordinal_position
        """)
        return {"table": table, "columns": columns}

    elif db == "mysql":
        columns = query_mysql(conn, f"DESCRIBE {table}")
        return {"table": table, "columns": columns}

    elif db == "sqlite":
        rows = query_sqlite(conn, f"PRAGMA table_info({table})")
        return {
            "table": table,
            "columns": [{"name": r["name"], "type": r["type"], "nullable": not r["notnull"], "primary": r["pk"] > 0} for r in rows]
        }

    return {}


def get_indexes(db: str, conn: str, table: str) -> list[dict]:
    """Get indexes for table."""
    if db == "postgres":
        return query_postgres(conn, f"""
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE tablename = '{table}'
        """)
    elif db == "sqlite":
        rows = query_sqlite(conn, f"PRAGMA index_list({table})")
        result = []
        for r in rows:
            details = query_sqlite(conn, f"PRAGMA index_info({r['name']})")
            result.append({"name": r["name"], "unique": r["unique"], "columns": [d["name"] for d in details]})
        return result
    return []


def main():
    if len(sys.argv) < 2:
        print("Usage: db-query.py <command> [args]")
        print("Commands:")
        print("  detect                           Detect database connection")
        print("  tables                           List all tables")
        print("  schema --table <name>            Show table schema")
        print("  columns --table <name>           Show columns")
        print("  indexes --table <name>          Show indexes")
        print("  fks --table <name>               Show foreign keys")
        sys.exit(1)

    cmd = sys.argv[1]

    # Detect connection
    detection = detect_connection()
    if not detection and cmd != "detect":
        print("Error: No database connection detected. Run 'db-query.py detect' first.")
        sys.exit(1)

    db = detection["db"] if detection else None
    conn = detection["conn"] if detection else None

    if cmd == "detect":
        if detection:
            print(f"Detected: {db} @ {conn}")
        else:
            print("No database connection detected.")
            print("Set DATABASE_URL in .env or pg-connection in package.json")

    elif cmd == "tables":
        tables = list_tables(db, conn)
        print(json.dumps({"tables": tables, "count": len(tables)}, indent=2))

    elif cmd == "schema":
        table = None
        if "--table" in sys.argv:
            idx = sys.argv.index("--table")
            table = sys.argv[idx + 1]
        else:
            print("Error: specify --table <name>")
            sys.exit(1)

        schema = get_schema(db, conn, table)
        print(json.dumps(schema, indent=2, default=str))

    elif cmd == "columns":
        table = None
        if "--table" in sys.argv:
            idx = sys.argv.index("--table")
            table = sys.argv[idx + 1]
        else:
            print("Error: specify --table <name>")
            sys.exit(1)

        schema = get_schema(db, conn, table)
        print(json.dumps(schema, indent=2, default=str))

    elif cmd == "indexes":
        table = None
        if "--table" in sys.argv:
            idx = sys.argv.index("--table")
            table = sys.argv[idx + 1]
        else:
            print("Error: specify --table <name>")
            sys.exit(1)

        indexes = get_indexes(db, conn, table)
        print(json.dumps({"table": table, "indexes": indexes}, indent=2, default=str))

    elif cmd == "fks":
        table = None
        if "--table" in sys.argv:
            idx = sys.argv.index("--table")
            table = sys.argv[idx + 1]
        else:
            print("Error: specify --table <name>")
            sys.exit(1)

        if db == "postgres":
            fks = query_postgres(conn, f"""
                SELECT 
                    tc.constraint_name, kcu.column_name,
                    ccu.table_name AS foreign_table_name,
                    ccu.column_name AS foreign_column_name
                FROM information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu ON tc.constraint_name = kcu.constraint_name
                JOIN information_schema.constraint_column_usage AS ccu ON ccu.constraint_name = tc.constraint_name
                WHERE tc.table_name = '{table}' AND tc.constraint_type = 'FOREIGN KEY'
            """)
            print(json.dumps({"table": table, "foreign_keys": fks}, indent=2))
        else:
            print("Foreign key introspection only supported for PostgreSQL")

    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()
