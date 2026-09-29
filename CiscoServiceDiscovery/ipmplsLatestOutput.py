import pandas as pd
import pyodbc

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

INPUT_CSV = r"IpmplsCustomerData.csv"
OUTPUT_FILE = r"filtered_db_output.csv"

DB_CONN_STR = (
    "DRIVER={ODBC Driver 18 for SQL Server};"
    "SERVER=172.28.3.181;"
    "DATABASE=GPONServiceDiscovery;"
    "UID=ossadmin;"
    "PWD=1q2w!Q@W;"
    "Encrypt=no;"
    "TrustServerCertificate=yes;"
)

DB_TABLE = "IpmplsServicesWholeData" 


# ─────────────────────────────────────────────
# STEP 1: Read CSV (FIXED)
# ─────────────────────────────────────────────

def clean_text(x):
    return str(x).strip().replace('\n', '').replace('\r', '').lower()

excel_df = pd.read_csv(INPUT_CSV, sep='\t')

# Clean column names
excel_df.columns = excel_df.columns.str.strip()

# Rename required columns
excel_df = excel_df.rename(columns={
    "Monitoring IP": "host_ip",
    "Monitoring Interface": "interface"
})

# Remove invalid rows
excel_df = excel_df[
    excel_df["host_ip"].notna() &
    excel_df["interface"].notna()
]

# Remove unwanted values
excel_df = excel_df[
    ~excel_df["host_ip"].str.contains("Not", case=False, na=False) &
    ~excel_df["interface"].str.contains("Not", case=False, na=False)
]

excel_df["host_ip"] = excel_df["host_ip"].apply(clean_text)
excel_df["interface"] = excel_df["interface"].apply(clean_text)


# Clean values
# excel_df["host_ip"] = excel_df["host_ip"].astype(str).str.strip()
# excel_df["interface"] = excel_df["interface"].astype(str).str.strip()

# Normalize interface (important)
# def normalize_interface(x):
#     x = str(x).strip().lower()
#     x = x.replace("gi", "")   # remove Gi
#     x = x.replace("te", "")   # remove TenGig if exists
#     return x

excel_df["interface"] = excel_df["interface"]

# ─────────────────────────────────────────────
# STEP 2: Fetch DB Data
# ─────────────────────────────────────────────

conn = pyodbc.connect(DB_CONN_STR)

query = f"""
SELECT hostname, host_ip, interface, status, protocol, description
FROM {DB_TABLE}
"""

db_df = pd.read_sql(query, conn)
conn.close()

db_df["host_ip"] = db_df["host_ip"].apply(clean_text)
db_df["interface"] = db_df["interface"].apply(clean_text)

# Clean DB data
db_df["host_ip"] = db_df["host_ip"].astype(str).str.strip()
db_df["interface"] = db_df["interface"].astype(str).str.strip()

# Normalize DB interface same way
db_df["interface"] = db_df["interface"]

# ─────────────────────────────────────────────
# STEP 3: Match using key
# ─────────────────────────────────────────────

print("\n🔍 DEBUG CHECK")

test_ips = ["172.16.3.48", "172.16.3.47"]

for ip in test_ips:
    print(f"\n--- Checking IP: {ip} ---")

    print("Excel:")
    print(excel_df[excel_df["host_ip"] == ip])

    print("DB:")
    print(db_df[db_df["host_ip"] == ip])


filtered_db = pd.merge(
    db_df,
    excel_df[["host_ip", "interface"]],
    on=["host_ip", "interface"],
    how="inner"
)

# excel_df["key"] = excel_df["host_ip"] + "_" + excel_df["interface"]
# db_df["key"] = db_df["host_ip"] + "_" + db_df["interface"]

# filtered_db = db_df[db_df["key"].isin(excel_df["key"])]

# # Keep only DB columns
# filtered_db = filtered_db.drop(columns=["key"])

# ─────────────────────────────────────────────
# STEP 4: Save Output
# ─────────────────────────────────────────────

filtered_db.to_csv(OUTPUT_FILE, index=False)

print("✅ Done! Output saved:", OUTPUT_FILE)
print("Matched rows:", len(filtered_db))



