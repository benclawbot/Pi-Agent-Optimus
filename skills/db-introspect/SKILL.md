---
name: db-introspect
description: Introspect database schemas without running the app. Use when "show tables", "schema", "database structure", "columns", "indexes", or "introspect database".
allowed-tools: Read,Bash
---

# Database Introspection

Query database schemas directly — no app required.

## Supported Databases

| Database | Command |
|----------|---------|
| PostgreSQL | `psql` or `pg_dump` |
| MySQL | `mysql` |
| SQLite | `sqlite3` |
| SQL Server | `sqlcmd` |

## Usage

### List All Tables

```bash
python scripts/db-query.py tables --db postgres --conn "postgresql://user:pass@localhost/db"
```

### Show Table Schema

```bash
python scripts/db-query.py schema --db postgres --conn "..." --table users
```

### Show Columns

```bash
python scripts/db-query.py columns --db postgres --conn "..." --table users
```

### Show Indexes

```bash
python scripts/db-query.py indexes --db postgres --conn "..." --table users
```

### Show Foreign Keys

```bash
python scripts/db-query.py fks --db postgres --conn "..." --table users
```

## Connection Detection

Auto-detect database from project files:
- `pg-connection` label in `package.json`
- `.env` file with `DATABASE_URL`
- `knexfile.js` / `prisma/schema.prisma`
- `docker-compose.yml` with database service

## Output Format

```json
{
  "tables": [
    {
      "name": "users",
      "columns": [
        {"name": "id", "type": "uuid", "nullable": false, "primary": true},
        {"name": "email", "type": "varchar(255)", "nullable": false}
      ],
      "indexes": [...],
      "foreign_keys": [...]
    }
  ]
}
```

## Integration

- With `skill-evolution` to capture schema patterns
- Use with migrations to understand current state
- Helpful for writing database tests

## Security

- Never store passwords in output
- Mask sensitive column data
- Require explicit connection string

## File Structure

```
db-introspect/
├── SKILL.md
└── scripts/
    └── db-query.py
```
