import pyodbc
import pandas as pd
import sys

# --- DATABASE CONNECTION DETAILS ---
# These are the details you provided.
SERVER = '172.28.3.181'
DATABASE = 'GPONServiceDiscovery'
UID = 'ossuser'
PWD = '1q2w!Q@W'
TABLE_NAME = 'GPONServiceDiscovery.dbo.GPONServices'

# --- CONFIGURATION ---
# IMPORTANT: This must match the exact name of the driver installed on your machine.
# Common names: 'ODBC Driver 17 for SQL Server', 'ODBC Driver 13 for SQL Server'
# UPDATED to use ODBC Driver 18 as confirmed by user.
ODBC_DRIVER_NAME = 'ODBC Driver 18 for SQL Server'


def test_sql_connection():
    """
    Attempts to connect to SQL Server and retrieve the first 5 rows of the specified table.
    """
    # 1. Define the ODBC Connection String
    # NOTE: You MUST have the specified ODBC Driver installed.
    conn_string = (
        f'DRIVER={{{ODBC_DRIVER_NAME}}};'
        f'SERVER={SERVER};'
        f'DATABASE={DATABASE};'
        f'UID={UID};'
        f'PWD={PWD};'
        f'Connection Timeout=10;'  # Set a timeout to quickly fail if the firewall is blocking it
        f'TrustServerCertificate=yes'  # FIX: Tell the driver to trust the self-signed or untrusted certificate
    )

    try:
        print(f"Connecting to SQL Server at {SERVER} using driver: {ODBC_DRIVER_NAME}...")

        # 2. Establish the connection
        with pyodbc.connect(conn_string) as conn:
            print("✅ Connection successful. Running query...")

            # 3. Define and execute the query
            query = f"SELECT TOP 5 * FROM {TABLE_NAME}"

            # Using pandas to easily execute the query and display results
            df = pd.read_sql(query, conn)

            # 4. Display the results
            print(f"\n--- First 5 rows from {TABLE_NAME} ---")
            print(df)
            print(f"\nSuccessfully read {len(df)} rows and {len(df.columns)} columns.")

    except pyodbc.Error as ex:
        # This block catches connection errors (like the SocketTimeout you saw in Metabase)
        sqlstate = ex.args[0]
        if 'Timeout expired' in str(ex) or 'timed out' in str(ex):
            print("\n❌ CONNECTION FAILED: TIMEOUT/FIREWALL ISSUE.")
            print(
                "The network path is likely blocked. You must open TCP Port 1433 on the server's firewall (172.28.3.181).")
        elif 'IM002' in str(sqlstate):
            print("\n❌ CONNECTION FAILED: DRIVER NOT FOUND (IM002).")
            print(f"Driver '{ODBC_DRIVER_NAME}' was not found on your system.")
            print("Please ensure you have installed the exact Microsoft ODBC Driver for SQL Server.")
            print(
                "Alternatively, check your installed drivers (using the ODBC Data Sources Administrator) and update the ODBC_DRIVER_NAME variable in the script.")
        elif 'Login failed' in str(ex):
            print("\n❌ CONNECTION FAILED: LOGIN FAILED.")
            print("The network is open, but the username or password is not accepted by the SQL Server.")
            print(f"Server accepted the connection but rejected UID: {UID}.")
        else:
            print(f"\n❌ CONNECTION FAILED: {sqlstate}")
            print(f"Error details: {ex}")
            print("Check credentials, server name, and driver installation.")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")

    print("\nScript finished.")


if __name__ == "__main__":
    test_sql_connection()
