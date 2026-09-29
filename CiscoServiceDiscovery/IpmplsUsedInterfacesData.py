"""
push_ipmpls_used_interfaces.py
────────────────────────────────
Reads one or more IPMPLS service-discovery CSV files, keeps ONLY rows
that have a non-empty `description` (i.e. USED interfaces — same rule
as the router/switch discovery scripts: has description = used,
regardless of up/down), cleans out any leaked header rows, and pushes
the result into SQL Server.

SAFETY: uses the same staging-table + atomic-swap pattern as the
router/switch discovery scripts. The LIVE table (IpmplsLatestData) is
NEVER truncated directly — only the staging table is, and it's only
promoted to live after a successful run. If this script crashes or
the CSVs are somehow empty/broken, your live table is left untouched.

ONE-TIME SETUP required before first run (creates the staging table):
    SELECT * INTO dbo.IpmplsLatestData_Staging FROM dbo.IpmplsLatestData WHERE 1 = 0;

Usage:
    pip install pandas pyodbc
    python push_ipmpls_used_interfaces.py
    python push_ipmpls_used_interfaces.py --input IPMPLSServiceDiscovery_here_new.csv
    python push_ipmpls_used_interfaces.py --input file1.csv file2.csv
    python push_ipmpls_used_interfaces.py --no-swap   (test run, staging only)
"""

import argparse
import logging
import pandas as pd
import pyodbc

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

DEFAULT_CSV_FILES = [
    "IPMPLSServiceDiscovery_here_new.csv",
]

TABLE_NAME         = "IpmplsUsedInterfacesData"
TABLE_NAME_STAGING = "IpmplsUsedInterfacesData_Staging"
TABLE_NAME_BACKUP  = "IpmplsUsedInterfacesData_Old"  # transient name used only during the swap

DB_CONN_STR = (
    "DRIVER={ODBC Driver 18 for SQL Server};"
    "SERVER=172.28.3.181;"
    "DATABASE=GPONServiceDiscovery;"
    "UID=ossadmin;"
    "PWD=1q2w!Q@W;"
    "Encrypt=no;"
    "TrustServerCertificate=yes;"
)

REQUIRED_COLUMNS = ["hostname", "host_ip", "interface", "status", "protocol", "description"]

# Minimum fraction of rows (after cleaning) that must have a real, non-empty
# description before we trust the run enough to promote it to live. This is
# NOT "% of interfaces that are used" — it just guards against a completely
# empty or garbage CSV silently wiping the live table.
MIN_USED_ROWS = 1

# ─────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("ipmpls_push.log", encoding="utf-8"),
    ],
)
log = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# CLEANING
# ─────────────────────────────────────────────

def clean_text(x):
    return str(x).strip().replace("\n", "").replace("\r", "")


def load_and_clean(csv_files: list) -> pd.DataFrame:
    frames = []
    for path in csv_files:
        log.info(f"Reading {path} ...")
        df = pd.read_csv(path, dtype=str)
        log.info(f"  {len(df)} raw rows")
        frames.append(df)

    df = pd.concat(frames, ignore_index=True)
    df.columns = df.columns.str.strip()

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Input CSV(s) missing required columns: {missing}")

    before = len(df)

    # Remove leaked header rows — case-insensitively, since a stray header
    # can appear as "Interface"/"STATUS"/"Protocol"/"Description" in any
    # casing depending on how the source data was captured.
    header_mask = (
        df["interface"].astype(str).str.strip().str.lower().eq("interface")
        | df["status"].astype(str).str.strip().str.lower().eq("status")
        | df["protocol"].astype(str).str.strip().str.lower().eq("protocol")
    )
    dropped_headers = header_mask.sum()
    df = df[~header_mask]

    # Remove completely empty rows
    df = df.dropna(how="all")

    # Fill NaN, clean whitespace/newlines on every column
    df = df.fillna("")
    for col in df.columns:
        df[col] = df[col].apply(clean_text)

    # De-dup on host_ip + interface (same device+port shouldn't repeat)
    before_dedup = len(df)
    df = df.drop_duplicates(subset=["host_ip", "interface"])
    dropped_dupes = before_dedup - len(df)

    df = df.astype(str)

    log.info(f"  Dropped {dropped_headers} leaked header row(s)")
    log.info(f"  Dropped {dropped_dupes} duplicate row(s)")
    log.info(f"  {len(df)} rows remain after cleaning (from {before} raw)")

    return df


def filter_used_only(df: pd.DataFrame) -> pd.DataFrame:
    """
    Keep only USED interfaces: description is non-empty after stripping.
    Matches the same rule as the router/switch discovery scripts —
    up/down status is irrelevant; only presence of a description counts.
    """
    before = len(df)
    used = df[df["description"].str.strip() != ""]
    log.info(f"  {len(used)} / {before} rows have a description (USED) — {before - len(used)} FREE rows excluded")
    return used


# ─────────────────────────────────────────────
# DB
# ─────────────────────────────────────────────

def get_db_connection():
    return pyodbc.connect(DB_CONN_STR, autocommit=True)


def push_to_staging(conn, df: pd.DataFrame):
    cursor = conn.cursor()

    log.info(f"Truncating {TABLE_NAME_STAGING} (staging area, NOT the live table)...")
    cursor.execute(f"TRUNCATE TABLE {TABLE_NAME_STAGING};")
    conn.commit()

    columns = ",".join(df.columns)
    placeholders = ",".join(["?"] * len(df.columns))
    insert_query = f"INSERT INTO {TABLE_NAME_STAGING} ({columns}) VALUES ({placeholders})"

    data = [tuple(row) for row in df.to_numpy()]

    try:
        cursor.fast_executemany = True
        cursor.executemany(insert_query, data)
        conn.commit()
        log.info(f"  ✅ Inserted {len(data)} rows into {TABLE_NAME_STAGING}")
        return len(data)
    except Exception as e:
        conn.rollback()
        log.error(f"  ❌ Insert failed: {e}")
        log.error(f"  Sample row causing issue: {data[:3]}")
        raise
    finally:
        cursor.close()


def swap_staging_into_live(conn):
    """
    Atomically promote IpmplsLatestData_Staging to be the new
    IpmplsLatestData, via a rename-based 3-way swap inside a transaction.
    The live table is never without data at any point.
    """
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN TRANSACTION;")
        cursor.execute(f"""
            IF OBJECT_ID('{TABLE_NAME_BACKUP}', 'U') IS NOT NULL
                DROP TABLE {TABLE_NAME_BACKUP};
        """)
        cursor.execute(f"EXEC sp_rename '{TABLE_NAME}', '{TABLE_NAME_BACKUP}';")
        cursor.execute(f"EXEC sp_rename '{TABLE_NAME_STAGING}', '{TABLE_NAME}';")
        cursor.execute(f"EXEC sp_rename '{TABLE_NAME_BACKUP}', '{TABLE_NAME_STAGING}';")
        cursor.execute("COMMIT TRANSACTION;")
        log.info(f"  ✅ Swap complete — {TABLE_NAME} now holds today's data.")
    except Exception as e:
        cursor.execute("ROLLBACK TRANSACTION;")
        log.error(f"  ❌ Swap failed, live table left untouched: {e}")
        raise
    finally:
        cursor.close()


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Push USED-only IPMPLS interfaces to SQL Server")
    parser.add_argument("--input", nargs="+", default=DEFAULT_CSV_FILES, help="One or more input CSV files")
    parser.add_argument("--no-swap", action="store_true", help="Populate staging only, don't promote to live")
    args = parser.parse_args()

    log.info("=" * 60)
    log.info("IPMPLS Used-Interface Push")
    log.info("=" * 60)

    df = load_and_clean(args.input)
    used_df = filter_used_only(df)

    print("\n🔍 Data Preview (used interfaces only):")
    print(used_df.head(5))
    print(f"Total USED rows to insert: {len(used_df)}")

    if len(used_df) < MIN_USED_ROWS:
        log.error(
            f"Only {len(used_df)} used row(s) found — below MIN_USED_ROWS ({MIN_USED_ROWS}). "
            f"Refusing to touch the database at all. Check your input CSV(s)."
        )
        return

    conn = get_db_connection()
    try:
        pushed = push_to_staging(conn, used_df)

        if args.no_swap:
            log.info("--no-swap set: staging table populated, live table left untouched.")
        elif pushed == 0:
            log.error("Zero rows pushed — refusing to swap. Live table left untouched.")
        else:
            swap_staging_into_live(conn)
    finally:
        conn.close()

    log.info("=" * 60)
    log.info("DONE")
    log.info("=" * 60)


if __name__ == "__main__":
    main()