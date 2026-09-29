import pandas as pd
from concurrent.futures import ThreadPoolExecutor
from CiscoInfoGrabber import CiscoInfoGrabber


# Function to process each router
def process_router(row):
    ip = row['ip_address']
    grabber = CiscoInfoGrabber(ip)
    grab = grabber.get_router_info()
    if len(grab) < 3:
        print(f"Error processing router {ip}:")

# Read the Excel file (limit to first 50 rows as an example)
static_file_df = pd.read_excel('Routers -All Pkgs.xlsx', engine='openpyxl', nrows=50)


# Use ThreadPoolExecutor for multithreading
def main():
    with ThreadPoolExecutor(max_workers=200) as executor:
        futures = [executor.submit(process_router, row) for _, row in static_file_df.iterrows()]

        # Wait for all threads to complete
        for future in futures:
            future.result()  # This will raise exceptions if any thread failed


# Run the main function
if __name__ == "__main__":
    main()
