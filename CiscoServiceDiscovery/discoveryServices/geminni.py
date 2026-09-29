import re
import pandas as pd
from typing import List, Dict, Any
from netmiko import ConnectHandler, NetmikoBaseException, NetmikoTimeoutException

# IMPORTANT: Fill in your actual device details here
ROUTER_IP = "172.16.3.49"
SWITCH_IP = "172.16.22.54"
# USERNAME = "praveen.j"  # Replace with your SSH username
USERNAME = "govindareddy.b"
PASSWORD = "hided"  # Replace with your SSH password
SECRET = "your_enable_secret"  # Replace with your enable/privileged mode password
TARGET_VRF = "GI_BB_SERVICES"

# --- 1. LIVE NETWORK CONNECTION CLASS ---

class LiveNetwork:
    """
    Handles SSH connection, command execution, and context management using Netmiko.
    """

    def __init__(self, ip: str, username: str, password: str, secret: str, device_type: str = 'cisco_ios'):
        self.ip = ip
        self.hostname = ""
        self.connection = None
        self.device_type = device_type
        self.connection_args = {
            'device_type': device_type,
            'host': ip,
            'username': username,
            'password': password,
            'secret': secret,
            'global_delay_factor': 2,  # Increase delay factor for slower connections
        }

    def __enter__(self):
        """Establish the connection upon entering the 'with' block."""
        try:
            print(f"Attempting to connect to {self.ip}...")
            self.connection = ConnectHandler(**self.connection_args)
            self.connection.enable()
            self.hostname = self.connection.base_prompt
            print(f"Successfully connected to {self.hostname} ({self.ip})")
            return self

        except NetmikoTimeoutException:
            raise Exception(f"Connection timeout to {self.ip}. Check IP or firewall.")
        except NetmikoBaseException as e:
            raise Exception(f"Netmiko error connecting to {self.ip}: {e}")
        except Exception as e:
            raise Exception(f"General error connecting to {self.ip}: {e}")

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Close the connection upon exiting the 'with' block."""
        if self.connection:
            self.connection.disconnect()
            print(f"Connection closed to {self.hostname}.")

    def send_command(self, command: str) -> str:
        """Sends a command and returns the raw output."""
        print(f"  > Executing: {command}")
        return self.connection.send_command(command, use_textfsm=False)


# --- 2. EXTRACTION LOGIC ---

def extract_router_data(router: LiveNetwork, vrf_name: str) -> List[Dict[str, Any]]:
    """Executes all router-side commands sequentially to gather data."""
    print(f"\n[ROUTER] 1. Identifying BDI interfaces for VRF '{vrf_name}'...")

    # 1. Identify BDI interfaces for the target VRF
    bdi_output = router.send_command(f"sh ip vrf {vrf_name}")

    # --- DEBUGGING STEP: Show the raw output we received ---
    print("\n--- RAW VRF OUTPUT RECEIVED (For Debugging) ---")
    print(bdi_output)
    print("-------------------------------------------------")
    # --------------------------------------------------------

    # FIX: Using a more flexible regex. It looks for the VRF name, skips the Default RD,
    # and captures everything that follows until the end of the output, assuming the
    # interfaces list is the final piece of information.
    pattern = re.compile(
        rf'{re.escape(vrf_name)}\s+[\w\.\:]+.*?([\w\s\-\_]+)$',
        re.DOTALL | re.MULTILINE
    )
    bdi_match = pattern.search(bdi_output)

    if bdi_match:
        # Capture group 1 contains the interfaces string (e.g., 'BD3301\nBD3302')
        interface_list_string = bdi_match.group(1)

        # Filter the captured words to only include BDI/BD interfaces
        bdi_interfaces = [
            iface.strip()
            for iface in interface_list_string.split()
            if iface.strip().startswith('BD')
        ]

        if not bdi_interfaces:
            print(f"Error: Found VRF block, but no interfaces starting with 'BD' were detected.")
            return []
    else:
        print(f"Error: Could not find VRF '{vrf_name}' entry in output. Check VRF name or command output format.")
        return []

    service_data = []
    port_channel_map = {}

    print(f"Interfaces found: {', '.join(bdi_interfaces)}")
    print("[ROUTER] 2. Capturing L3 details (IP/Mask/Description) and L2 bindings...")
    for bdi in bdi_interfaces:
        # Note: BDI is typically BDIXXXX, the BD ID is XXXX
        bd_id = bdi.replace('BDI', '').replace('BD', '')

        # a) Get L3 details (sh run int BDIXXXX)
        # Note: The BD interface might be BDIXXXX or BDXXXX depending on router type
        l3_output = router.send_command(f"sh run int {bdi}")

        desc_match = re.search(r'description\s+(.+)', l3_output)
        # Regex to capture both the IP and the Mask
        ip_match = re.search(r'ip address\s+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\s+\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})',
                             l3_output)

        # b) Get L2 binding details (sh bridge-domain XXXX)
        l2_output = router.send_command(f"sh bridge-domain {bd_id}")

        # Capture the Port-channel service instance string
        l2_link_match = re.search(r'(Port-channel\d+\s+service\s+instance\s+\d+)', l2_output)

        l2_link = 'N/A'
        port_channel = 'N/A'

        if l2_link_match:
            l2_link = l2_link_match.group(1).strip()
            # Extract Port-channel number (e.g., '30' from 'Port-channel30')
            po_match = re.search(r'Port-channel(\d+)', l2_link)
            port_channel = f'Po{po_match.group(1)}' if po_match else 'N/A'
            port_channel_map[port_channel] = port_channel

        # Store initial data
        service_data.append({
            'Router_Hostname': router.hostname,
            'Service_VRF': vrf_name,
            'BDI_Interface': bdi,
            'Bridge_Domain': bd_id,
            'BDI_Description': desc_match.group(1).strip() if desc_match else 'N/A',
            'IP_Address': ip_match.group(1).strip() if ip_match else 'N/A',
            'L2_Service_Link': l2_link,
            'Port_Channel': port_channel,
        })

    # 3. Get physical ports from etherchannel summary (common to all instances)
    print("[ROUTER] 3. Getting Port-channel physical interfaces...")
    ether_output = router.send_command("sh etherchannel summary")
    physical_ports = {}

    for po in port_channel_map.keys():
        po_id = po.replace('Po', '')
        # Regex to match the Port-channel line and capture the ports (P for bundled)
        # Example: 30      Po30(RU)                      Gi0/0/9(P)
        po_line_match = re.search(rf'^{po_id}\s+{po}\(R[UDS]\)\s+.*?\s+([\w\/\-\.]+)\(P\)', ether_output, re.MULTILINE)
        physical_ports[po] = po_line_match.group(1) if po_line_match else 'N/A'

    # 4. Get VLAN, Service Policy, and CIR details
    print("[ROUTER] 4. Getting VLAN, Service Policy, and CIR details...")
    all_po_details = {}

    if port_channel_map:
        po_name = next(iter(port_channel_map.keys()))  # Assuming all BDs share one upstream Po
        po_run_output = router.send_command(f"sh run int {po_name}")

        # Capture all service instances inside the port-channel
        service_instance_blocks = re.findall(r'service instance (\d+) ethernet\s+(.*?)(?=service instance|\Z)',
                                             po_run_output, re.DOTALL)

        for instance_id, block in service_instance_blocks:
            if instance_id in [s['Bridge_Domain'] for s in service_data]:
                vlan_match = re.search(r'encapsulation dot1q (\d+)', block)
                policy_match = re.search(r'service-policy input (\S+)', block)

                vlan_id = vlan_match.group(1) if vlan_match else 'N/A'
                policy_name = policy_match.group(1) if policy_match else 'N/A'

                # Get CIR from policy map
                cir = 'N/A'
                if policy_name != 'N/A':
                    policy_output = router.send_command(f"sh policy-map {policy_name}")
                    # Capture the CIR value (a number)
                    cir_match = re.search(r'police cir (\d+)\s+bc', policy_output)
                    cir = cir_match.group(1) if cir_match else 'N/A'

                all_po_details[instance_id] = {
                    'VLAN_ID': vlan_id,
                    'Service_Policy': policy_name,
                    'CIR_bps': cir
                }

    # Update the service_data list with the newly fetched details
    for item in service_data:
        bd_id = item['Bridge_Domain']
        po_name = item['Port_Channel']

        item['Router_Physical_Port'] = physical_ports.get(po_name, 'N/A')

        if bd_id in all_po_details:
            item.update(all_po_details[bd_id])
        else:
            item.update({'VLAN_ID': 'N/A', 'Service_Policy': 'N/A', 'CIR_bps': 'N/A'})

    # 5. Get Switch IP from ARP table (BDI500/TFIBER-IP-MGMT)
    print("[ROUTER] 5. Identifying Last Mile Switch IP...")
    arp_output = router.send_command("SH IP ARP VRF TFIBER-IP-MGMT BDI500")

    switch_ip = 'N/A'
    router_bdi_ip = "172.16.22.53"  # Assumed router IP based on your sample output

    for line in arp_output.split('\n'):
        match = re.search(r'Internet\s+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s+\d+', line)
        if match:
            ip_address = match.group(1)
            if ip_address != router_bdi_ip:
                switch_ip = ip_address
                break

    # Add switch IP to all records
    for item in service_data:
        item['Switch_IP'] = switch_ip

    return service_data


def extract_switch_data(switch: LiveNetwork, router_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Executes all switch-side commands to find ports."""

    if not router_data:
        return []

    # 1. Get the physical port connecting to the router Po
    print("[SWITCH] 6. Getting Switch Uplink Port from Port-channel 1...")
    # Assumes the uplink to the router is Po1 on the switch side based on the example
    po1_output = switch.send_command("sh interfaces port-channel 1")
    uplink_match = re.search(r'Po1\s+Active:\s+(\w+)', po1_output)
    switch_uplink_port = uplink_match.group(1) if uplink_match else 'N/A'

    # 2. Get customer access ports based on VLANs
    print("[SWITCH] 7. Getting Customer Access Ports from VLANs...")
    vlan_port_map = {}

    # Collect unique VLANs to query
    unique_vlans = {item['VLAN_ID'] for item in router_data if item['VLAN_ID'] != 'N/A'}

    for vlan in unique_vlans:
        # Note: some Cisco switches use 'sh vlan tag X', others 'sh vlan id X' or 'sh vlan brief'
        vlan_output = switch.send_command(f"sh vlan tag {vlan}")

        # Regex to capture the Untagged Ports column
        # Example line: 3301        3301               Po1                gi2                  S
        # Captures the word in the 4th column from the start, before the 'S' or 'D' flag
        untagged_port_match = re.search(r'^\s*' + str(vlan) + r'\s+.*\s+(\w+)\s+[SDGV]', vlan_output, re.MULTILINE)
        customer_port = untagged_port_match.group(1).strip() if untagged_port_match else 'N/A'
        vlan_port_map[vlan] = customer_port

    # 3. Update the router_data with switch details
    for item in router_data:
        item['Switch_Uplink_Port'] = switch_uplink_port
        vlan = item['VLAN_ID']
        item['Customer_Access_Port'] = vlan_port_map.get(vlan, 'N/A')

    return router_data


# --- 3. MAIN EXECUTION AND DATA REPHRASING ---

def main():
    """Main function to run the script."""

    if not all([ROUTER_IP, USERNAME, PASSWORD, SECRET]):
        print("ERROR: Please update the CONFIGURATION & CREDENTIALS section at the top of the script.")
        return

    extracted_router_data = []

    # Use 'with' context manager to ensure connections are properly closed
    try:
        # Connect to Router
        with LiveNetwork(ROUTER_IP, USERNAME, PASSWORD, SECRET, 'cisco_ios') as router:
            extracted_router_data = extract_router_data(router, TARGET_VRF)
    except Exception as e:
        print(f"\nFATAL ERROR during router extraction: {e}")
        return

    if not extracted_router_data:
        print("\nProcess failed: No service interfaces found on the router.")
        return

    # Connect to Switch (using the configured static switch IP for simplicity)
    final_data = []
    try:
        print(f"\n--- Switching connection to Last Mile Switch ({SWITCH_IP}) ---")
        with LiveNetwork(SWITCH_IP, USERNAME, PASSWORD, SECRET, 'cisco_ios') as switch:
            final_data = extract_switch_data(switch, extracted_router_data)
    except Exception as e:
        print(f"\nFATAL ERROR during switch extraction: {e}")
        # If switch fails, we still proceed with router data
        final_data = extracted_router_data
        for item in final_data:
            item['Switch_Uplink_Port'] = 'SWITCH CONNECT FAILED'
            item['Customer_Access_Port'] = 'SWITCH CONNECT FAILED'

    # 4. Data Rephrasing and Consolidation
    print("\n--- Finalizing Data and Creating DataFrame ---")

    df = pd.DataFrame(final_data)

    # Convert CIR from bps to Mbps for readability
    df['CIR_Mbps'] = df['CIR_bps'].apply(lambda x: round(int(x) / 1000000, 2) if str(x).isdigit() else x)

    # Define the final, rephrased column order and names
    final_columns = [
        'Router_Hostname', 'Service_VRF', 'BDI_Interface', 'Bridge_Domain', 'VLAN_ID',
        'IP_Address', 'CIR_Mbps', 'Service_Policy', 'BDI_Description',
        'L2_Service_Link', 'Port_Channel', 'Router_Physical_Port',
        'Switch_IP', 'Switch_Uplink_Port', 'Customer_Access_Port',
    ]

    df_final = df.reindex(columns=final_columns)

    df_final.columns = [
        'Router Hostname', 'VRF Name', 'Routed BDI Interface', 'Bridge Domain ID',
        'Customer VLAN ID', 'Service L3 IP/Mask', 'CIR (Mbps)', 'QoS Service Policy',
        'Interface Description (Customer Name)', 'L2 Service Instance Link',
        'Router Port-Channel', 'Router Physical Port', 'Last Mile Switch IP',
        'Switch Uplink Port (to Router)', 'Customer Access Port (on Switch)',
    ]

    # 5. Convert to CSV
    csv_filename = f"{TARGET_VRF}_live_service_details.csv"
    df_final.to_csv(csv_filename, index=False)

    print(f"\n--- SUCCESS ---")
    print(f"Data for {TARGET_VRF} successfully processed and saved to {csv_filename}")
    print("\nFinal DataFrame Head:")
    print(df_final.head().to_string())


if __name__ == "__main__":
    main()