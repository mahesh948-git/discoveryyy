#This script is to update IPMPLS devices status in Services Inventory(ServicesMasterLatestData) table

import pyodbc
import schedule
import time
from datetime import datetime

# ─────────────────────────────────────────────
# DB CONFIG
# ─────────────────────────────────────────────

DB_CONN_STR = (
    "DRIVER={ODBC Driver 18 for SQL Server};"
    "SERVER=172.28.3.181;"
    "DATABASE=Availability;"   # main DB
    "UID=ossuser;"
    "PWD=1q2w!Q@W;"
    "Encrypt=no;"
    "TrustServerCertificate=yes;"
)

# ─────────────────────────────────────────────
# QUERY
# ─────────────────────────────────────────────

NORMALIZE_QUERY_1 = """
UPDATE GPONServiceDiscovery.dbo.IpmplsLatestData
SET status = 'UP'
WHERE status = 'up';
"""

NORMALIZE_QUERY_2 = """
UPDATE GPONServiceDiscovery.dbo.IpmplsLatestData
SET status = 'DOWN'
WHERE status = 'down';
"""

UPDATE_QUERY = """
UPDATE A
SET A.final_status = B.status
FROM Availability.dbo.ServicesMasterLatestData A
INNER JOIN GPONServiceDiscovery.dbo.IpmplsLatestData B
    ON A.[OLT IP Address] = B.host_ip
WHERE A.[Hand Off] = 'Ipmpls'
AND B.status IS NOT NULL;
"""

# UPDATE_QUERY = """
# UPDATE A
# SET A.final_status = 
#     CASE 
#         WHEN UPPER(B.status) = 'UP' THEN 'UP'
#         WHEN UPPER(B.status) = 'DOWN' THEN 'DOWN'
#         ELSE A.final_status   -- keep existing if something else
#     END
# FROM Availability.dbo.ServicesMasterLatestData A
# INNER JOIN GPONServiceDiscovery.dbo.IpmplsLatestData B
#     ON A.[OLT IP Address] = B.host_ip
# WHERE A.[Hand Off] = 'Ipmpls'
# AND B.status IS NOT NULL;
# """

# ─────────────────────────────────────────────
# JOB FUNCTION
# ─────────────────────────────────────────────

def update_status():
    try:
        conn = pyodbc.connect(DB_CONN_STR)
        cursor = conn.cursor()

        # Step 1: Normalize
        cursor.execute(NORMALIZE_QUERY_1)
        cursor.execute(NORMALIZE_QUERY_2)

        # Step 2: Update final table
        cursor.execute(UPDATE_QUERY)

        conn.commit()

        print(f"✅ Updated successfully at {datetime.now()}")

        conn.close()

    except Exception as e:
        print(f"❌ Error at {datetime.now()}:", str(e))


# ─────────────────────────────────────────────
# SCHEDULER (every 30 minutes)
# ─────────────────────────────────────────────

schedule.every(1).hour.do(update_status)

print("Scheduler started... running every 1 hour")

# Run once immediately (optional but useful)
update_status()

# Keep script running
while True:
    schedule.run_pending()
    time.sleep(5)