import os
import glob
import time
import json
import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text
import urllib
from datetime import datetime
import mail

# print(f"Started at: {datetime.now()}")

def current_date():
    ist = datetime.now()
    ist_12hr_format = ist.strftime("%d_%b(%I-%M%p)")

    return ist_12hr_format

date_today = current_date()
full_path = None
full_path_by_customer = None


# ============================================================
# NEW: ONT "first seen" date tracking
# ------------------------------------------------------------
# GPONServices is a daily-snapshot table (cleanup deletes rows
# with ReportDate < today before every insert), so it cannot be
# used to remember when an ONT Serial Number was first detected.
# This function uses a separate, persistent tracking table
# (dbo.ONTFirstSeenTracking) that is never cleaned up, to record
# each ONT Serial Number's Record Added Date exactly once.
#
# Rules implemented:
#   - Tracking table empty (very first run)  -> 'Existing/Unknown'
#   - Serial not seen before                 -> today's date, stored
#   - Serial already tracked                 -> original stored date is
#                                                returned (retained, never overwritten)
# ============================================================
def get_or_track_ont_first_seen(engine, ont_serials, today_display_date):
    # NOTE: SQL Server's default collation is case-insensitive, so
    # 'TJNW957DB6BC' and 'tjnw957db6bc' are the SAME primary key to SQL
    # Server even though Python treats them as different strings. Source
    # files sometimes have the same physical ONT serial in different
    # casing across rows, so we normalize to uppercase here to make the
    # Python-side dedup match SQL Server's dedup and avoid duplicate-key
    # errors on insert.
    ont_serials = [
        str(s).strip().upper() for s in set(ont_serials)
        if s is not None and str(s).strip() != '' and str(s).strip().lower() != 'nan'
    ]
    ont_serials = list(set(ont_serials))

    with engine.begin() as conn:
        # Create tracking table once if it doesn't exist yet (never dropped/cleaned)
        conn.execute(text("""
            IF NOT EXISTS (
                SELECT 1 FROM sys.tables t
                JOIN sys.schemas s ON t.schema_id = s.schema_id
                WHERE t.name = 'ONTFirstSeenTracking' AND s.name = 'dbo'
            )
            CREATE TABLE dbo.ONTFirstSeenTracking (
                ONTSerialNumber NVARCHAR(100) NOT NULL PRIMARY KEY,
                RecordAddedDate NVARCHAR(20) NOT NULL
            );
        """))

        existing_count = conn.execute(
            text("SELECT COUNT(*) FROM dbo.ONTFirstSeenTracking")
        ).scalar()
        is_initial_bootstrap = (existing_count == 0)

        existing_rows = conn.execute(
            text("SELECT ONTSerialNumber, RecordAddedDate FROM dbo.ONTFirstSeenTracking")
        ).fetchall()
        tracked_map = {row[0]: row[1] for row in existing_rows}

        new_serials = [s for s in ont_serials if s not in tracked_map]

        if new_serials:
            assign_date = 'Existing/Unknown' if is_initial_bootstrap else today_display_date
            insert_rows = [{'serial': s, 'added_date': assign_date} for s in new_serials]
            conn.execute(
                text("""
                    INSERT INTO dbo.ONTFirstSeenTracking (ONTSerialNumber, RecordAddedDate)
                    VALUES (:serial, :added_date)
                """),
                insert_rows
            )
            for s in new_serials:
                tracked_map[s] = assign_date

    return tracked_map


def push_data():
    try:
        def insert_data(file):
            df = pd.read_csv(file)

            # SQL Server connection
            params = urllib.parse.quote_plus(
                'DRIVER={ODBC Driver 18 for SQL Server};'
                'SERVER=172.28.3.181;'
                'DATABASE=GPONServiceDiscovery;'
                'UID=ossuser;'
                'PWD=1q2w!Q@W;'
                'TrustServerCertificate=yes;'
            )
            engine = create_engine(f'mssql+pyodbc:///?odbc_connect={params}')

            # Execute cleanup query before inserting
            with engine.begin() as conn:
                cleanup_query = text("""
                    DELETE FROM GPONServiceDiscovery.dbo.GPONServices
                    WHERE ReportDate < CAST(GETDATE() - 0 AS DATE);
                """)
                conn.execute(cleanup_query)
                print("[INFO] Deleted records older than 2 days")

                # Insert into SQL
                df.to_sql(name='GPONServices', con=conn, schema='dbo', if_exists='append', index=False)
                print("[SUCCESS]Data inserted into [dbo].[GPONServices] successfully.")

        def insert_data_by_customer(file):
            df1 = pd.read_csv(file)

            # SQL Server connection
            params = urllib.parse.quote_plus(
                'DRIVER={ODBC Driver 18 for SQL Server};'
                'SERVER=172.28.3.181;'
                'DATABASE=GPONServiceDiscovery;'
                'UID=ossuser;'
                'PWD=1q2w!Q@W;'
                'TrustServerCertificate=yes;'
            )
            engine = create_engine(f'mssql+pyodbc:///?odbc_connect={params}')

            # Execute cleanup query before inserting
            with engine.begin() as conn:
                cleanup_query = text("""
                          DELETE FROM GPONServiceDiscovery.dbo.GPONServicesByCustomer
                          WHERE ReportDate < CAST(GETDATE() - 0 AS DATE);
                      """)
                conn.execute(cleanup_query)
                print("[INFO]Deleted records older than 3 days")

                # Insert into SQL
                df1.to_sql(name='GPONServicesByCustomer', con=conn, schema='dbo', if_exists='append', index=False)
                print("[SUCCESS]Data inserted into [dbo].[GPONServicesByCustomer] successfully.")

        tejas_path = r'E:\PycharmProjects\TejasServiceDiscovery\Reports'
        nokia_path = r'E:\PycharmProjects\NokiaServiceDiscovery\Reports'

        def get_latest_file_24hrs(folder_path, extension="*"):
            search_pattern = os.path.join(folder_path, f'*.{extension}') if extension != "*" else os.path.join(folder_path, '*')
            files = [f for f in glob.glob(search_pattern) if os.path.isfile(f)]
            if not files:
                return None
            now = time.time()
            cutoff = now - 20 * 60 * 60
            recent_files = [f for f in files if os.path.getmtime(f) >= cutoff]
            if not recent_files:
                return None
            latest_file = max(recent_files, key=os.path.getmtime)
            return latest_file

        tejas_df = pd.read_excel(get_latest_file_24hrs(tejas_path), engine='openpyxl')
        nokia_df = pd.read_excel(get_latest_file_24hrs(nokia_path), engine='openpyxl')
        df = pd.concat([tejas_df, nokia_df], ignore_index=True)

        # ============================================================
        # NEW: shared inventory DB connection (used by Stage 1 and Stage 2)
        # ============================================================
        inv_params = urllib.parse.quote_plus(
            'DRIVER={ODBC Driver 18 for SQL Server};'
            'SERVER=172.28.3.86;'
            'DATABASE=MFSM;'
            'UID=powerbi;'
            'PWD=Hyderabad@32;'
            'TrustServerCertificate=yes;'
        )
        inv_engine = create_engine(f'mssql+pyodbc:///?odbc_connect={inv_params}')

        df['Node IP'] = df['Node IP'].astype(str).str.strip()

        def _blank(column):
            return df[column].isna() | (df[column].astype(str).str.strip() == '')

        # ============================================================
        # STAGE 1: ALLInventory1 — OLT Hostname, OLT Location, OLT Model, ONT Model
        # (checked FIRST, per priority)
        # ============================================================
        inventory_df = pd.read_sql(
            "SELECT IP_Address, Hostname, Site_Name, LGD_Code, Node_Type, Device_Type FROM dbo.ALLInventory1",
            inv_engine
        )
        inventory_df['IP_Address'] = inventory_df['IP_Address'].astype(str).str.strip()
        inventory_df['Device_Type'] = inventory_df['Device_Type'].astype(str).str.strip().str.upper()

        lgd_clean = inventory_df['LGD_Code'].astype(str).str.strip().str.replace(r'\.0$', '', regex=True)
        inventory_df['OLT_Location_Lookup'] = inventory_df['Site_Name'].astype(str).str.strip() + '_' + lgd_clean

        # Hostname/Location come from OLT-type rows
        hostname_loc_lookup = inventory_df[inventory_df['Device_Type'] == 'OLT'][
            ['IP_Address', 'Hostname', 'OLT_Location_Lookup']
        ].drop_duplicates(subset='IP_Address').rename(
            columns={'IP_Address': 'Node IP', 'Hostname': '_lkp_hostname', 'OLT_Location_Lookup': '_lkp_location'}
        )

        # OLT Model from OLT-type rows' Node_Type
        olt_model_lookup1 = inventory_df[inventory_df['Device_Type'] == 'OLT'][
            ['IP_Address', 'Node_Type']
        ].drop_duplicates(subset='IP_Address').rename(
            columns={'IP_Address': 'Node IP', 'Node_Type': '_lkp_olt_model1'}
        )

        # ONT Model from ONT-type rows' Node_Type (matched by IP only — ALLInventory1 has no per-ONT key)
        ont_model_lookup1 = inventory_df[inventory_df['Device_Type'] == 'ONT'][
            ['IP_Address', 'Node_Type']
        ].drop_duplicates(subset='IP_Address').rename(
            columns={'IP_Address': 'Node IP', 'Node_Type': '_lkp_ont_model1'}
        )

        df = df.merge(hostname_loc_lookup, on='Node IP', how='left')
        df = df.merge(olt_model_lookup1, on='Node IP', how='left')
        df = df.merge(ont_model_lookup1, on='Node IP', how='left')

        df['OLT Hostname'] = df['OLT Hostname'].where(~_blank('OLT Hostname'), df['_lkp_hostname'])
        df['OLT Location'] = df['OLT Location'].where(~_blank('OLT Location'), df['_lkp_location'])
        df['OLT Model'] = df['OLT Model'].where(~_blank('OLT Model'), df['_lkp_olt_model1'])
        df['ONT Model'] = df['ONT Model'].where(~_blank('ONT Model'), df['_lkp_ont_model1'])

        df.drop(columns=['_lkp_hostname', '_lkp_location', '_lkp_olt_model1', '_lkp_ont_model1'], inplace=True)

        # ============================================================
        # STAGE 2: ALLInventory — fills whatever is STILL blank after Stage 1
        # OLT Model (by IP) + ONT Model (by IP + ONT ID)
        # ============================================================
        allinv_df = pd.read_sql(
            "SELECT device_name, ipaddress, subcategory, device_model FROM dbo.ALLInventory",
            inv_engine
        )
        allinv_df['ipaddress'] = allinv_df['ipaddress'].astype(str).str.strip()
        allinv_df['device_model'] = allinv_df['device_model'].astype(str).str.strip()

        junk_values = {'datana', 'na', '', 'none', 'null', 'nan'}
        allinv_df = allinv_df[~allinv_df['device_model'].str.lower().isin(junk_values)]

        olt_lookup2 = allinv_df[allinv_df['subcategory'].str.upper() == 'OLT'][['ipaddress', 'device_model']]
        olt_lookup2 = olt_lookup2.drop_duplicates(subset='ipaddress').rename(
            columns={'ipaddress': 'Node IP', 'device_model': '_lkp_olt_model2'}
        )

        ont_lookup2 = allinv_df[allinv_df['subcategory'].str.upper() == 'ONT'].copy()
        ont_lookup2['_ont_id_key'] = ont_lookup2['device_name'].astype(str).str.split('|').str[-1].str.strip()
        ont_lookup2 = ont_lookup2.drop_duplicates(subset=['ipaddress', '_ont_id_key'])[['ipaddress', '_ont_id_key', 'device_model']]
        ont_lookup2 = ont_lookup2.rename(columns={'ipaddress': 'Node IP', 'device_model': '_lkp_ont_model2'})

        df['ONT ID'] = df['ONT ID'].astype(str).str.strip()
        df['_ont_id_key'] = df['ONT ID']

        df = df.merge(olt_lookup2, on='Node IP', how='left')
        df = df.merge(ont_lookup2, on=['Node IP', '_ont_id_key'], how='left')

        df['OLT Model'] = df['OLT Model'].where(~_blank('OLT Model'), df['_lkp_olt_model2'])
        df['ONT Model'] = df['ONT Model'].where(~_blank('ONT Model'), df['_lkp_ont_model2'])

        df.drop(columns=['_lkp_olt_model2', '_ont_id_key', '_lkp_ont_model2'], inplace=True)

        # ============================================================
        # STAGE 3: Tejas EMS raw API JSON — fallback for OLT Hostname/Location
        # (covers OLTs commissioned in Tejas but not yet synced into ALLInventory1)
        # ============================================================
        tejas_api_dir = r'E:\PycharmProjects\TejasServiceDiscovery\Tejaspackage(API_responses)'
        api_ip_lookup = {}

        for pkg_letter in ['A', 'B', 'C']:
            olt_json_path = os.path.join(tejas_api_dir, f'TejasPkg{pkg_letter}olt.json')
            if not os.path.exists(olt_json_path):
                continue
            try:
                with open(olt_json_path, 'r', encoding='utf-8') as f:
                    olt_nodes = json.load(f)
                for node in olt_nodes:
                    info = {item.get('value-name'): item.get('value') for item in node.get('additional-information', [])}
                    ip = info.get('mename')
                    if ip:
                        api_ip_lookup[ip.strip()] = {
                            'hostname': info.get('nativeEMSName'),
                            'location': info.get('location'),
                        }
            except Exception as e:
                print(f"[INFO]Could not parse {olt_json_path}: {e}")

        if api_ip_lookup:
            hostname_map = {ip: v['hostname'] for ip, v in api_ip_lookup.items() if v.get('hostname')}
            location_map = {ip: v['location'] for ip, v in api_ip_lookup.items() if v.get('location')}

            mapped_hostname = df['Node IP'].map(hostname_map)
            mapped_location = df['Node IP'].map(location_map)

            df['OLT Hostname'] = df['OLT Hostname'].where(~_blank('OLT Hostname'), mapped_hostname)
            df['OLT Location'] = df['OLT Location'].where(~_blank('OLT Location'), mapped_location)

        today_date = datetime.now().strftime('%Y-%m-%d')

        df['ReportDate'] = today_date

        df['SVLAN'] = pd.to_numeric(df['SVLAN'], errors='coerce')

        # NEW: fill missing SVLAN using the digits after '_S' (or trailing '_<digits>') in Service Name
        svlan_from_name = pd.to_numeric(
            df['Service Name'].astype(str).str.extract(r'(?:[_-]S|_)(\d+)$')[0], errors='coerce'
        )
        df['SVLAN'] = df['SVLAN'].fillna(svlan_from_name)

        df['Type of Service'] = np.where(
            df['SVLAN'].between(200, 299, inclusive="both"),
            'Internal MGMT',
            'Customer Service'
        )

        # ============================================================
        # NEW: Record Added Date — first-seen date per ONT Serial Number
        # ============================================================
        # Normalize casing here too, so it matches the tracking table's key
        # (SQL Server's PK collation is case-insensitive; see note in
        # get_or_track_ont_first_seen). This also keeps rows for the same
        # physical ONT consistent within this run's report/grouping.
        df['ONT Serial Number'] = df['ONT Serial Number'].astype(str).str.strip().str.upper()

        record_added_date_today = datetime.now().strftime('%d-%b-%Y')  # e.g. 22-Sep-2026

        tracking_params = urllib.parse.quote_plus(
            'DRIVER={ODBC Driver 18 for SQL Server};'
            'SERVER=172.28.3.181;'
            'DATABASE=GPONServiceDiscovery;'
            'UID=ossuser;'
            'PWD=1q2w!Q@W;'
            'TrustServerCertificate=yes;'
        )
        tracking_engine = create_engine(f'mssql+pyodbc:///?odbc_connect={tracking_params}')

        ont_serial_list = df['ONT Serial Number'].dropna().unique().tolist()
        first_seen_map = get_or_track_ont_first_seen(tracking_engine, ont_serial_list, record_added_date_today)

        df['Record Added Date'] = df['ONT Serial Number'].map(first_seen_map).fillna('Existing/Unknown')

        global full_path
        full_path = f'Reports/{date_today}GPONServices.csv'
        global full_path_by_customer
        full_path_by_customer = f'Reports/{date_today}GPONServices_ByCustomer.csv'

        print("Original Columns:", df.columns, df.shape)

        new_columns = [
            'ReportDate', 'Vendor', 'Package', 'OLT Hostname', 'OLT Location',
            'ONT Port', 'Service Name', 'Type of Service', 'Service Type', 'Uplink Port', 'SVLAN',
            'Traffic Type', 'Node IP', 'CVLAN', 'Upstream Profile Name',
            'Downstream Profile Name', 'ONT ID', 'ONT Serial Number', 'Record Added Date',
            'ONT Location', 'ONT Model', 'Pon Port', 'OLT Model',
            'Upstream Max Bandwidth', 'Upstream Assured Bandwidth',
            'Upstream Fixed Bandwidth', 'DownstreamPIR', 'DownstreamCIR'
        ]
        df = df[new_columns]
        # df["DownstreamPIR"] = None
        # df["DownstreamCIR"] = None
        print("Reordered Columns:", df.columns, df.shape)
        
        print(full_path)
        print(os.path.exists(full_path))
        
        try:
            with open(full_path, "a"):
                pass
            print("File is writable")
        except Exception as e:
            print("File is locked:", e)

        df.to_csv(full_path, index=False)

        def combine_values(series):
            non_null = series.dropna()
            non_null = non_null[non_null.astype(str).str.strip() != '']
            unique_vals = non_null.unique()
            if len(unique_vals) == 0:
                return np.nan
            if len(unique_vals) == 1:
                return str(unique_vals[0])
            return ', '.join(map(str, unique_vals))

        new_df = df.groupby(['Package', 'OLT Hostname', 'ONT Serial Number'], as_index=False).agg(
            combine_values)

        # new_df["DownstreamPIR"] = None
        # new_df["DownstreamCIR"] = None

        new_df.to_csv(full_path_by_customer, index=False)

        insert_data(full_path)
        insert_data_by_customer(full_path_by_customer)

        return True, None
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return False, str(e)

# cc_mails = ['SAYYAD.PASHA@Ltts.com' ,'Sivaprasad.Yeparala@LTTS.com', 'Sandeep.Deshmukh@LTTS.com', 'Jayant.Madavi@Ltts.com']
# Emails = ['guggilla.rishik@ltts.com', 'Ritik.Kumar@Ltts.com', 'gangatharun.maddikera@ltts.com', 'nagajyothi.pavuluri@ltts.com',]

Emails = ['AbbisettiSai.Supraja@ltts.com', 'Vemudala.Mahesh@ltts.com']
cc_mails = ['Sivaprasad.Yeparala@LTTS.com']

# Emails = ['AbbisettiSai.Supraja@ltts.com']
# cc_mails = ['Sivaprasad.Yeparala@LTTS.com']
if __name__ == "__main__":
        try:
            ip_path = r'E:\PycharmProjects\ServiceDiscoveryMain\IPReports\IPMPLSServiceDiscovery.csv'
            status, msg = push_data()
            if status:
                subject = f'Status of ServiceDiscovery at {date_today} - Success.'
                body = (
                    f'Hi team,\n\nPlease find the latest attached ServiceDiscovery files.\nReport Auto Generated at {date_today}.\n\nBest Regards,'
                    f'\nAutomated HealthChecker\n\nDisclaimer: This is an automated email, please do not reply to this message.\n\n')

                mail.send_mail_2(Emails,cc_mails, subject, body, full_path, ip_path, full_path_by_customer)
                print("Passed ... ")
            else:
                subject = f'Status of GPONServiceDiscovery at {date_today} - Failed.'
                body = (
                    f'Hi team,\n\nFailed Fetching ServiceDiscovery, Error: {msg}.\nReport Auto Generated at {date_today}.\n\nBest Regards,'
                    f'\nAutomated HealthChecker\n\nDisclaimer: This is an automated email, please do not reply to this message.\n\n')

                mail.send_mail(Emails, [], subject, body, None)

        except Exception as e:
            subject = f'Status of GPONServiceDiscovery at {date_today} - Failed.'
            body = (
                f'Hi team,\n\nFailed Fetching ServiceDiscovery, Error: {e}.\nReport Auto Generated at {date_today}.\n\nBest Regards,'
                f'\nAutomated HealthChecker\n\nDisclaimer: This is an automated email, please do not reply to this message.\n\n')
            mail.send_mail(Emails, [], subject, body, None)