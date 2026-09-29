import os
from datetime import datetime, timedelta
import logging
import pandas as pd

# Define the log file path
log_file = 'serviceDiscoveryLogs.log'

# Required file identifiers

# Configure logging
logging.basicConfig(
    filename=log_file,
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def file_processing(pkg_x):
    required_files = {
        'PORT_S_C_VLAN': None,
        'OLT_VLAN_LIST': None,
        'OSS_NE_DATA': None,
        'OSS_ONT_DATA': None,
        'Chassis_Uplink_Service': None,
        'ONT_Download': None,
        'ONT_Upload': None,
        'OLT_Download': None,
        'OLT_Upload': None
    }

    today = datetime.today().date()
    yesterday = today - timedelta(days=1)

    if not os.path.exists(pkg_x):
        logging.error(f"Failed: The directory {pkg_x} does not exist.")
        return None

    file_names = os.listdir(pkg_x)
    fetched_today = set()

    for file_name in file_names:
        file_path = os.path.join(pkg_x, file_name)
        if os.path.isfile(file_path):
            modified_time = datetime.fromtimestamp(os.path.getmtime(file_path)).date()
            for key in required_files.keys():
                if key in file_name and required_files[key] is None:
                    if modified_time == today:
                        required_files[key] = file_name
                        fetched_today.add(key)

    fetched_yesterday = set()
    if None in required_files.values():
        for file_name in file_names:
            file_path = os.path.join(pkg_x, file_name)
            if os.path.isfile(file_path):
                modified_time = datetime.fromtimestamp(os.path.getmtime(file_path)).date()
                for key in required_files.keys():
                    if key in file_name and required_files[key] is None:
                        if modified_time == yesterday:
                            required_files[key] = file_name
                            fetched_yesterday.add(key)
    if len(fetched_today) == len(required_files):
        logging.info(f"Success: All required files have been fetched for package {pkg_x} from today files")
    elif len(fetched_today) + len(fetched_yesterday) == len(required_files):
        logging.info(f"Success: All required files have been fetched for package {pkg_x} from today and yesterday files")
    else:
        missing_files = [key for key, value in required_files.items() if value is None]
        logging.error(f"Failed: Missing files for package {pkg_x}: {missing_files}")

    return required_files

def cleanup_old_files(directory, keep_dates):
    """Deletes files older than the specified keep_dates (set of dates to keep)."""
    try:
        for file_name in os.listdir(directory):
            file_path = os.path.join(directory, file_name)
            if os.path.isfile(file_path):
                modified_time = datetime.fromtimestamp(os.path.getmtime(file_path)).date()
                if modified_time not in keep_dates:
                    os.remove(file_path)
    except Exception as e:
        logging.error(f"Error while deleting old files: {e}")

def clean_csv(file_path):
    """Reads a CSV file and removes rows with extra or missing columns."""
    try:
        # Read only the header to determine the correct number of columns
        with open(file_path, "r", encoding="utf-8") as f:
            header = f.readline().strip().split(",")  # Read header row
            expected_columns = len(header)

        # Read file and ensure all rows match the header's column count
        df = pd.read_csv(file_path, names=header, skiprows=1, on_bad_lines="skip", dtype=str)
        df = df[df.apply(lambda row: len(row) == expected_columns, axis=1)]  # Keep only valid rows
        return df

    except Exception as e:
        print(f"Error processing file {file_path}: {e}")
        return pd.DataFrame()
