import pyodbc
import pandas as pd
from netmiko import ConnectHandler

# ─────────────────────────────────────────────
# DB CONFIG
# ─────────────────────────────────────────────

DB_CONN_STR = (
    "DRIVER={ODBC Driver 18 for SQL Server};"
    "SERVER=172.28.3.181;"
    "DATABASE=GPONServiceDiscovery;"
    "UID=ossadmin;"
    "PWD=1q2w!Q@W;"
    "Encrypt=no;"
    "TrustServerCertificate=yes;"
)

TABLE_NAME = "IpmplsServicesWholeData"   


#Script for IPMPLS Service 

hosts = ["172.16.3.47","172.16.3.49", "172.16.3.58","172.16.80.225", "172.16.80.227", 
         "172.16.6.51","10.253.192.131","172.16.3.48","172.16.6.64","172.16.0.184","172.17.128.1","172.17.224.1"]
hostnames = ["RRDSHAMXGPR001","HYBDCCSXGPR001", "HYDSRNIDGPR001", "HYDTGSECMAR001", "HYBDGAPSMAG001", 
             "GACHCPCOGPR001","KBAJNORXMAR001","RRRRJNRXGPR001","HYDBRAIGGP001","SECURASOGPR001","NOCTESTGAC001","NOCTESTMAR001"]

# username = "praveen.j"
# password = "Nasa@1021"
username = "govindareddy.b"
password = "J!f@b&r&987654"
cmd = "show int description"

rows = []
for h, hn in zip(hosts, hostnames):
    dev = {"device_type": "cisco_ios", "host": h, "username": username, "password": password}
    try:
        with ConnectHandler(**dev) as con:
            out = con.send_command(cmd)
    except Exception as e:
        print(f"Failed {h} ({hn}): {e}")
        continue

    for ln in out.splitlines():
        if not ln.strip():
            continue
        parts = ln.split()
        if len(parts) >= 4:
            intf = parts[0]
            # handle "admin down" as one status
            if parts[1] == "admin" and parts[2] == "down":
                status = "admin down"
                proto = parts[3]
                desc = " ".join(parts[4:])
            else:
                status = parts[1]
                proto = parts[2]
                desc = " ".join(parts[3:])
            if status.lower() in ["up"]:
                status = "UP"
            elif "down" in status.lower():
                status = "DOWN"
            else:
                status = status.upper()
            desc = desc.strip("#* ")
            rows.append({
                "hostname": hn,
                "host_ip": h,
                "interface": intf,
                "status": status,
                "protocol": proto,
                "description": desc
            })

df = pd.DataFrame(rows, columns=["hostname", "host_ip", "interface", "status", "protocol", "description"])
print(df.to_string(index=False))
df.to_csv("IPMPLSServiceDiscovery_here_new.csv", index=False)


# ─────────────────────────────────────────────
# INSERT INTO DB
# ─────────────────────────────────────────────

conn = pyodbc.connect(DB_CONN_STR)
cursor = conn.cursor()

# OPTIONAL: Clear table before insert
cursor.execute(f"TRUNCATE TABLE {TABLE_NAME}")
conn.commit()

# Prepare insert query
columns = ",".join(df.columns)
placeholders = ",".join(["?"] * len(df.columns))

insert_query = f"INSERT INTO {TABLE_NAME} ({columns}) VALUES ({placeholders})"

# Convert DataFrame to list of tuples
data = [tuple(x) for x in df.to_numpy()]

# Fast insert
cursor.fast_executemany = True
cursor.executemany(insert_query, data)

conn.commit()
conn.close()

print("✅ Data inserted into DB successfully")