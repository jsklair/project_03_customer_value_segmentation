from pathlib import Path
import sqlite3
import sys


# Anchor paths to the repository root so the script is independent
# of the current PowerShell working directory.
PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATABASE_FILE = (
    PROJECT_ROOT
    / "data"
    / "database"
    / "online_retail.db"
)


def split_sql_statements(sql_text: str) -> list[str]:
    """Split a SQL file into complete SQLite statements."""

    statements = []
    buffer = []

    # sqlite3.complete_statement() understands SQL syntax well enough to
    # distinguish statement-ending semicolons from semicolons inside comments
    # or quoted text. This is safer than splitting the raw file on ";".
    for line in sql_text.splitlines():
        buffer.append(line)
        candidate = "\n".join(buffer).strip()

        if candidate and sqlite3.complete_statement(candidate):
            statements.append(candidate)
            buffer = []

    remainder = "\n".join(buffer).strip()

    if remainder:
        raise ValueError(
            "SQL file ends with an incomplete statement. "
            "Check that the final SQL statement ends with a semicolon."
        )

    return statements


def run_sql_file(sql_file: Path) -> None:
    """Execute a SQL file and print the result of each result-returning statement."""

    if not DATABASE_FILE.exists():
        raise FileNotFoundError(
            f"SQLite database not found: {DATABASE_FILE}"
        )

    if not sql_file.exists():
        raise FileNotFoundError(
            f"SQL file not found: {sql_file}"
        )

    sql_text = sql_file.read_text(encoding="utf-8")
    statements = split_sql_statements(sql_text)

    result_number = 0

    with sqlite3.connect(DATABASE_FILE) as connection:
        for statement in statements:
            cursor = connection.execute(statement)

            # DROP, CREATE and other non-query statements do not return rows.
            if cursor.description is None:
                continue

            result_number += 1

            columns = [column[0] for column in cursor.description]
            rows = cursor.fetchall()

            print(f"\n--- Query {result_number} ---")
            print(" | ".join(columns))

            for row in rows:
                print(
                    " | ".join(
                        "NULL" if value is None else str(value)
                        for value in row
                    )
                )

        connection.commit()


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(
            "Usage: python python\\04_run_sql.py "
            "sql\\01_data_reconciliation.sql"
        )

    sql_file = Path(sys.argv[1])

    # A relative SQL path supplied from the project root is converted
    # explicitly to the corresponding repository file.
    if not sql_file.is_absolute():
        sql_file = PROJECT_ROOT / sql_file

    print(f"Database: {DATABASE_FILE}")
    print(f"SQL file: {sql_file}")

    run_sql_file(sql_file)


if __name__ == "__main__":
    main()