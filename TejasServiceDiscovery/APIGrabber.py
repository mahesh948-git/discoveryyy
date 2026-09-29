import os.path
import requests
import urllib3
import json
import math
import logging
import time

# --- Configuration ---

# Define the log file path and configure logging
log_file = 'serviceDiscoveryLogs.log'
# Configure logging to write to the file
logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
print(f"Logging configured. Output will be written to: {log_file}")

PKG_ENDPOINTS = {
    'A': '172.28.7.85',
    'B': '172.28.12.215',
    'C': '172.28.13.215',
}

# --- Utility Functions ---

def token_grabber(endpoint):
    """Grabs the JWT token for a given endpoint."""
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    headers = {
        "user": "NBIAdmin",
        "password": "NBIAdmin2023",
        "User-Agent": "PostmanRuntime/7.28.4",
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive"
    }
    url = f'https://{endpoint}:446/nmsnbi-rest/tapi/data/context/auth-context/auth-token'
    print(f"\nAttempting to grab token from {endpoint}...")

    try:
        response = requests.post(url, headers=headers, verify=False, timeout=30)
        response.raise_for_status()
        token = response.json()['jwt']
        print(f"✅ Token grabbed successfully for {endpoint}.")
        return token
    except requests.exceptions.RequestException as e:
        error_msg = f"Token acquisition failed for {endpoint}: {e}"
        logging.error(error_msg)
        print(f"❌ ERROR: {error_msg}")
        raise

def api_builder(pkg, endpoint):
    """Builds the dictionary of API endpoints based on the package."""
    # Ensure all URLs use f-string for endpoint
    base_url = f'https://{endpoint}:446/nmsnbi-rest/tapi/data/context'

    # Determine topology part
    topology_part = f'topology=TEJAS-T-FIBER-PKG{pkg}' if pkg in ('B', 'C') else 'topology=TEJAS-T-FIBER'

    return {
        'services': f'{base_url}/connectivity-context/connectivity-services/filter?configState=true&csType=Ethernet&continue=0&size=99999999',
        'olt': f'{base_url}/topology-context/{topology_part}/node?continue=0&size=999999',
        'ont_count': f'{base_url}/physical-context/device/equipment?category=ont',
        'ont': f'{base_url}/physical-context/device/equipment?category=ont&size=500&IsDuplicate=False',
        'downstream': f'{base_url}/connectivity-context/downstream-bandwidth-profile?continue=0&size=999999',
        'upstream': f'{base_url}/connectivity-context/upstream-bw-profile?continue=0&size=999999',
    }

def response_grabber(file_name, url, auth, params=None):
    """Fetches API response and saves it to a file."""
    if params is None:
        params = {}

    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    headers = {
        "Authorization": f"Bearer {auth}",
        "User-Agent": "PostmanRuntime/7.28.4",
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive"
    }

    output_file = f"Tejaspackage(API_responses)/TejasPkg{file_name}.json"
    print(f"  Fetching API: {file_name}...")

    response = None

    try:
        # Increase the timeout for Package A, or if the server is generally slow.
        # Let's set it to 600 seconds (10 minutes) for heavy requests.
        response = requests.get(url, headers=headers, params=params, verify=False, timeout=1200)
        response.raise_for_status()

        with open(output_file, 'w', encoding='utf-8') as file:
            json.dump(response.json(), file, indent=4, ensure_ascii=False)
            logging.info(f"Successfully saved {file_name}.json")
            print(f"  ✅ Saved to {output_file}")
            return response.headers

    except requests.exceptions.RequestException as e:
        # SAFELY check the status code/response text
        status_code = getattr(response, 'status_code', 'N/A')
        response_text = getattr(response, 'text', 'No response text available (Request failed before response).')

        error_msg = f"Failed to fetch {file_name} (Status Code: {status_code}): {type(e).__name__} - {e}"
        logging.error(error_msg)
        print(f"  ❌ ERROR: {error_msg}")
        # Only print response text if a response object exists AND we got a non-200 code
        if response is not None and status_code != 'N/A' and status_code >= 400:
            print(f"  Response Text (partial): {response_text[:100]}...")

        return False

    except json.JSONDecodeError:
        # This block is executed if a response was received (so 'response' exists) but it wasn't valid JSON.
        error_msg = f"Failed to decode JSON for {file_name}. Response text starts with: {response.text[:100]}..."
        logging.error(error_msg)
        print(f"  ❌ ERROR: {error_msg}")
        return False

# --- Main Sequential Processing Logic ---

def process_pkg_sequentially(pkg, endpoint):
    """Processes all API calls for a single package sequentially."""

    log_msg = f"Starting processing for package {pkg} at {endpoint}"
    logging.info(log_msg)
    print(f"\n--- {log_msg} ---")

    try:
        # 1. Get Token (only once per package)
        token = token_grabber(endpoint)
    except Exception:
        return False

    API_ENDPOINTS = api_builder(pkg, endpoint)

    # Process APIs
    for name, url in API_ENDPOINTS.items():
        full_file_name = f"{pkg}{name}"

        if name == 'ont':
            # This logic handles pagination for 'ont'
            try:
                ont_count_file = f'Tejaspackage(API_responses)/TejasPkg{pkg}ont_count.json'

                if not os.path.exists(ont_count_file):
                    warn_msg = f"Missing required file: {ont_count_file}. Cannot process 'ont'. Skipping."
                    logging.warning(warn_msg)
                    print(f"  ⚠️ WARNING: {warn_msg}")
                    continue

                with open(ont_count_file) as file:
                    list_length = len(json.load(file))

                page_size = 500
                count = int(math.ceil(list_length / page_size))
                print(f"  Starting pagination for {full_file_name}: Total items: {list_length}, Pages: {count}")

                header = '0'
                for i in range(count):
                    params = {'continue': header}

                    response_headers = response_grabber(f"{full_file_name}{i}", url, token, params=params)

                    if not response_headers:
                        warn_msg = f"Failed to fetch ont page {i} for {pkg}. Stopping pagination."
                        logging.warning(warn_msg)
                        print(f"  ⚠️ WARNING: {warn_msg}")
                        break

                    header = response_headers.get('continue', '-1')

                    if header == '-1':
                        info_msg = f"Pagination completed for {full_file_name} after {i + 1} pages."
                        logging.info(info_msg)
                        print(f"  {info_msg}")
                        break

            except Exception as e:
                error_msg = f"Error during 'ont' pagination for {pkg}: {e}"
                logging.error(error_msg)
                print(f"  ❌ ERROR: {error_msg}")
                continue

        else:
            # Handle all non-paginated endpoints
            if not response_grabber(full_file_name, url, token):
                warn_msg = f"Request for {full_file_name} failed. Continuing to next API in package {pkg}."
                logging.warning(warn_msg)
                print(f"  ⚠️ WARNING: {warn_msg}")

    info_msg = f"Completed processing for package {pkg}."
    logging.info(info_msg)
    print(f"--- {info_msg} ---\n")
    return True

# --- Execution ---

def json_files_creator():
    """Iterates through all packages and processes them sequentially."""
    all_success = True

    # Ensure the directory exists
    output_dir = "Tejaspackage(API_responses)"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        info_msg = f"Created output directory: {output_dir}"
        logging.info(info_msg)
        print(f"Directory: {info_msg}")

    for pkg, endpoint in PKG_ENDPOINTS.items():
        if not process_pkg_sequentially(pkg, endpoint):
            all_success = False
            logging.error(f"Processing failed for package {pkg}. Check logs for details.")

    return all_success


# --- Main Block to Run and Retry ---

MAX_RETRIES = 1

try:
    success = False
    for i in range(MAX_RETRIES):
        info_msg = f"Attempt {i + 1}/{MAX_RETRIES}: Starting file creation process."
        logging.info(info_msg)
        print(f"\n[GLOBAL] {info_msg}")

        if json_files_creator():
            final_msg = f"Success: All required files have been fetched for packages A, B, C."
            logging.info(final_msg)
            print(f"\n[GLOBAL] ✅ {final_msg}")
            success = True
            break
        else:
            warn_msg = f"Attempt {i + 1} failed. Retrying in 5 seconds..."
            logging.warning(warn_msg)
            print(f"\n[GLOBAL] ⚠️ {warn_msg}")
            time.sleep(5)

    if not success:
        critical_msg = f"Failed to fetch all files after {MAX_RETRIES} attempts."
        logging.critical(critical_msg)
        print(f"\n[GLOBAL] ❌ CRITICAL 1): {critical_msg}")

except Exception as e:
    critical_msg = f'Unhandled error during main execution: {e}'
    logging.critical(critical_msg)
    print(f"\n[GLOBAL] ❌ CRITICAL: {critical_msg}")