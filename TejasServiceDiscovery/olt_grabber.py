import pandas as pd
import json
from OLTObjectmaker import OLTObjectMaker
import logging

logging.basicConfig(
    filename="olt_debug.log",
    filemode="w",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logging.info("=" * 80)
logging.info("Starting OLT Debug")

olt_df = {
    'Vendor': [],
    'pacakge': [],
    'device': [],
    'District': [],
    'Location': [],
    'OLT IP': [],
    'OLT Name': [],
    'Product Name': [],
    'OLT Description': [],
    'SNMP Encryption Algorithm' : [],
    'Comm Protocol': [],
    'Ethernet IP': [],
    'Num of ONT connected' : [],
    'Operational Status' : [],
    'Admin Status' : [],
    'Physical/Comm Status' : [],
    'Creation Time': [],
    'Last Up Time' : [],
    'Last Down Time': [],
    'Modify Time': [],
    'Last Available Time': [],
    'Total Endpoints': [],
    'Upgraded Software Version': [],
    'Connected Ports' : [],
}

def olt_df_maker():
    pkgs = ['A', 'B', 'C']
    for pkg in pkgs:
        otl_path = f'Tejaspackage(API_responses)/TejasPkg{pkg}olt.json'

        with open(otl_path, 'r') as file:
            data = json.load(file)
            logging.info(f"Package-{pkg}: {len(data)} OLTs received from API")

        for item in data:
            olt_obj = OLTObjectMaker(item, pkg)
            logging.info(
                f"Package-{pkg} | "
                f"OLT={olt_obj.olt_name} | "
                f"IP={olt_obj.olt_ip} | "
                f"Location={olt_obj.location}"
            )
            olt_df['Vendor'].append(olt_obj.vendor)
            olt_df['pacakge'].append(olt_obj.pacakge)
            olt_df['device'].append(olt_obj.device)
            olt_df['District'].append(olt_obj.district)
            olt_df['Location'].append(olt_obj.location)
            olt_df['OLT IP'].append(olt_obj.olt_ip)
            olt_df['OLT Name'].append(olt_obj.olt_name)
            olt_df['Product Name'].append(olt_obj.product_name)
            olt_df['OLT Description'].append(olt_obj.description)
            olt_df['SNMP Encryption Algorithm'].append(olt_obj.snmp_encryption_algorithm)
            olt_df['Comm Protocol'].append(olt_obj.comm_protocol)
            olt_df['Ethernet IP'].append(olt_obj.ethernet_ip)
            olt_df['Num of ONT connected'].append(olt_obj.num_of_ont_connected)
            olt_df['Operational Status'].append(olt_obj.operational_status)
            olt_df['Admin Status'].append(olt_obj.admin_status)
            olt_df['Physical/Comm Status'].append(olt_obj.physical_comm_status)
            olt_df['Creation Time'].append(olt_obj.creation_time)
            olt_df['Last Up Time'].append(olt_obj.last_up_time)
            olt_df['Last Down Time'].append(olt_obj.last_down_time)
            olt_df['Modify Time'].append(olt_obj.modify_time)
            olt_df['Last Available Time'].append(olt_obj.last_available_time)
            olt_df['Total Endpoints'].append(olt_obj.node_endpoints)
            olt_df['Upgraded Software Version'].append(olt_obj.upgraded_software_version)
            olt_df['Connected Ports'].append(olt_obj.connected_ports)
            df = pd.DataFrame(olt_df)

            logging.info(f"Total OLT rows : {len(df)}")
            logging.info(f"Unique OLT IPs : {df['OLT IP'].nunique()}")

            duplicates = df[df.duplicated('OLT IP', keep=False)]

            if not duplicates.empty:
                logging.warning("Duplicate OLT IPs Found")
                logging.warning("\n" + duplicates.to_string())

            return df

    return pd.DataFrame(olt_df)
