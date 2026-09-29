import pandas as pd
import pyodbc

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

CSV_FILE_1 = r"IPMPLSServiceDiscovery_here_new.csv"
CSV_FILE_2 = r"filtered_db_output.csv"

TABLE_NAME = "IpmplsLatestData"

DB_CONN_STR = (
    "DRIVER={ODBC Driver 18 for SQL Server};"
    "SERVER=172.28.3.181;"
    "DATABASE=GPONServiceDiscovery;"
    "UID=ossadmin;"
    "PWD=1q2w!Q@W;"
    "Encrypt=no;"
    "TrustServerCertificate=yes;"
)

# ─────────────────────────────────────────────
# CLEANING FUNCTION
# ─────────────────────────────────────────────

def clean_text(x):
    return str(x).strip().replace('\n', '').replace('\r', '')

# ─────────────────────────────────────────────
# STEP 1: Read CSV Files
# ─────────────────────────────────────────────

df1 = pd.read_csv(CSV_FILE_1)
df2 = pd.read_csv(CSV_FILE_2)

# ─────────────────────────────────────────────
# STEP 2: Combine Data
# ─────────────────────────────────────────────

df = pd.concat([df1, df2], ignore_index=True)

# Clean column names
df.columns = df.columns.str.strip()

# ─────────────────────────────────────────────
# STEP 3: CLEAN DATA (IMPORTANT)
# ─────────────────────────────────────────────

# Remove accidental header rows
df = df[
    (df["interface"] != "Interface") &
    (df["status"] != "Status") &
    (df["protocol"] != "Protocol")
]

# Remove completely empty rows
df = df.dropna(how="all")

# Fill NaN values
df = df.fillna("")

# Apply cleaning to all columns
for col in df.columns:
    df[col] = df[col].apply(clean_text)

# Remove duplicates (based on key columns)
df = df.drop_duplicates(subset=["host_ip", "interface"])

# Convert all to string (safe for SQL)
df = df.astype(str)

# ─────────────────────────────────────────────
# STEP 4: DEBUG (optional but useful)
# ─────────────────────────────────────────────

print("\n🔍 Data Preview:")
print(df.head(5))
print("Total rows to insert:", len(df))

# ─────────────────────────────────────────────
# STEP 5: INSERT INTO SQL SERVER
# ─────────────────────────────────────────────

conn = pyodbc.connect(DB_CONN_STR)
cursor = conn.cursor()

# Optional: clear table before insert
cursor.execute(f"TRUNCATE TABLE {TABLE_NAME}")
conn.commit()

# Build insert query
columns = ",".join(df.columns)
placeholders = ",".join(["?"] * len(df.columns))
insert_query = f"INSERT INTO {TABLE_NAME} ({columns}) VALUES ({placeholders})"

# Convert to tuples
data = [tuple(row) for row in df.to_numpy()]

try:
    cursor.fast_executemany = True
    cursor.executemany(insert_query, data)
    conn.commit()
    print("✅ Data inserted successfully into table:", TABLE_NAME)

except Exception as e:
    print("❌ Insert failed:", e)
    print("👉 Sample row causing issue:", data[:5])

finally:
    conn.close()