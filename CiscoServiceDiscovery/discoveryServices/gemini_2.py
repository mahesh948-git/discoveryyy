import re
import pandas as pd
from typing import List, Dict, Any, Optional
from netmiko import ConnectHandler, NetmikoBaseException, NetmikoTimeoutException

# ====================================================================
# CONFIGURATION & CREDENTIALS
# IMPORTANT: Update these values with your actual network details
# ====================================================================
# USERNAME = "praveen.j"  # Replace with your SSH username
# PASSWORD = "Nasa@1021"  # Replace with your SSH password
username = 'govindareddy.b',
password = 'J!f@b&r&987654',
SECRET = "Nasa@1021"  # Replace with your enable/privileged mode password

# List of target routers (Complete list as provided)
ROUTER_TARGETS = [
    {"ip": "172.16.3.49", "hostname": "HYBDCCSXGPR001", "switch_ip_hint": "172.16.22.54"},
    {"ip": "172.16.3.58", "hostname": "HYDSRNIDGPR001", "switch_ip_hint": None},
    {"ip": "172.16.80.225", "hostname": "HYDTGSECMAR001", "switch_ip_hint": None},
    {"ip": "172.16.80.227", "hostname": "HYBDGAPSMAG001", "switch_ip_hint": None},
    {"ip": "172.16.6.51", "hostname": "GACHCPCOGPR001", "switch_ip_hint": None},
    {"ip": "172.16.80.60", "hostname": "RRDFRNRXMAR001", "switch_ip_hint": None},
    {"ip": "10.253.192.107", "hostname": "ADBICDAXMAR001", "switch_ip_hint": None},
    {"ip": "10.253.192.131", "hostname": "KBAJNORXMAR001", "switch_ip_hint": None},
    {"ip": "10.253.205.163", "hostname": "ADBSRKDXMAR001", "switch_ip_hint": None},
]

# TARGET_SERVICE_VRF_KEYWORDS is updated to ensure better filtering of relevant VRFs
TARGET_SERVICE_VRF_KEYWORDS = ["BB", "ILL", "SPOKE", "VPN", "SERVICE", "TDIA"]

# VRF used to find the Last Mile Switch IP via ARP
MGMT_VRF_FOR_ARP = "TFIBER-IP-MGMT"


# ====================================================================
# LIVE NETWORK CONNECTION CLASS (Optimized for Router Stability)
# ====================================================================

class LiveNetwork:
    """Handles SSH connection, command execution, and context management using Netmiko."""

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
            'global_delay_factor': 2,
            'fast_cli': False,
            'timeout': 45,
            'conn_timeout': 30,
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
            # Re-raise with a clear message about the timeout
            raise Exception(f"Connection timeout to {self.ip}. Check IP, firewall, or device load.")
        except NetmikoBaseException as e:
            # We catch Netmiko errors specifically to provide better feedback
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
        return self.connection.send_command(command, use_textfsm=False)


# ====================================================================
# CORE EXTRACTION FUNCTION (FIXED VRF DISCOVERY)
# ====================================================================

def get_all_vrf_names(router: LiveNetwork) -> List[str]:
    """
    Gets a list of all configured VRF names on the router using a robust method.
    FIX: Uses 'show vrf' and falls back to a looser regex on 'show ip vrf detail' if needed.
    """
    try:
        vrf_names = []

        # 1. Attempt the simpler 'show vrf' command first
        output = router.send_command("show vrf")

        # Simple line-by-line parsing for VRF names (usually the first word after header)
        for line in output.split('\n'):
            line = line.strip()
            # Skip header lines, empty lines, and system VRFs
            if not line or line.upper().startswith(('NAME', 'VRFID', 'VRF-NAME', '----', 'IP-VRF', 'DEFAULT')):
                continue

            # Extract the first word (the VRF name)
            match = re.match(r'^(\S+)', line)
            if match:
                vrf_names.append(match.group(1))

        # 2. If 'show vrf' failed to retrieve anything, fall back to 'show ip vrf detail'
        if not vrf_names:
            # Use the more detailed command
            output = router.send_command("show ip vrf detail")

            # Looser regex for 'show ip vrf detail' output to catch VRF definition blocks
            # It looks for a sequence of non-whitespace characters at the start of a line
            # that is followed by the common VRF definition markers.
            vrf_names = re.findall(r'^(\S+)(?:\s+RD:|\s+interfaces:|\s+\(vrf definition\))', output, re.MULTILINE)

        # Cleanup: Filter out ignored names and ensure uniqueness
        ignore_list = ["VPN", "VRF", "default", "VRF", "Global"]

        cleaned_names = sorted(list(set([name for name in vrf_names if name not in ignore_list])))

        if not cleaned_names:
            # If after all attempts, nothing is found, raise a controlled error
            raise Exception("No VRFs found or command output parsing failed.")

        return cleaned_names

    except Exception as e:
        print(f"  > WARNING: Failed to get VRF list. Error detail: {e}")
        return []


def extract_l3_services_by_vrf(router: LiveNetwork, vrf_name: str) -> List[Dict[str, Any]]:
    """
    Extracts L3 BDI services for a given VRF and determines connectivity type
    (Direct-CPE or Indirect-Switch/L2) based on the BDI's bridge-domain binding.
    """
    # Print less verbose message as we are iterating over ALL VRFs
    print(f"\n[ROUTER: {router.hostname}] Checking VRF '{vrf_name}'...")
    service_data = []

    # 1. Identify BDI interfaces for the target VRF
    vrf_output = router.send_command(f"sh ip vrf detail {vrf_name}")

    # Check if the output block indicates interfaces
    interface_list_block = re.search(r'Interfaces:(.*?)(?:\n\s*RD:|Total number of VRFs:|\Z)', vrf_output,
                                     re.DOTALL | re.IGNORECASE)

    if not interface_list_block:
        return []

    interface_list_string = interface_list_block.group(1)
    bdi_interfaces = [
        iface.strip()
        for iface in interface_list_string.split()
        # Look for BDI or BD interfaces
        if iface.strip().startswith(('BDI', 'BD'))
    ]

    if not bdi_interfaces:
        return []

    print(f"  > BDI Interfaces found: {', '.join(bdi_interfaces)} in VRF '{vrf_name}'")
    port_channel_map = {}

    # 2. Capture L3 details and L2 bindings for each BDI
    for bdi in bdi_interfaces:
        bd_id = bdi.replace('BDI', '').replace('BD', '')

        # a) Get L3 details (sh run int BDIXXXX)
        l3_output = router.send_command(f"sh run int {bdi}")
        desc_match = re.search(r'description\s+(.+)', l3_output)
        ip_match = re.search(r'ip address\s+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\s+\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})',
                             l3_output)

        # Get QoS policies
        policy_in_match = re.search(r'service-policy input\s+(\S+)', l3_output)
        policy_out_match = re.search(r'service-policy output\s+(\S+)', l3_output)

        # b) Get L2 binding details (sh bridge-domain XXXX)
        l2_output = router.send_command(f"sh bridge-domain {bd_id}")

        connectivity_type = 'N/A'
        port_channel_name = 'N/A'
        service_instance_id = 'N/A'
        router_physical_port = 'N/A'
        cpe_physical_interface = 'N/A'

        # Check 1: Port-channel link (Indirect-Switch/L2)
        po_link_match = re.search(r'(Port-channel\d+)\s+service\s+instance\s+(\d+)', l2_output)

        if po_link_match:
            connectivity_type = 'Indirect-Switch/L2'
            port_channel_name = po_link_match.group(1).strip()
            service_instance_id = po_link_match.group(2).strip()
            port_channel_map[port_channel_name] = port_channel_name

        # Check 2: Direct Physical Interface link (Direct-CPE)
        # Refined Regex for Direct Physical Port Match (Handles Te, Gi, Te0/8/4)
        phys_link_match = re.search(r'((?:Gi|Te|Fa|Eth|Bundle)\S+)\s+[LSDG]\s+(?:Up|Down)', l2_output)

        if phys_link_match and not po_link_match and 'Port-channel' not in phys_link_match.group(1):
            # If it has a direct physical link and was NOT marked as Po link
            connectivity_type = 'Direct-CPE'
            cpe_physical_interface = phys_link_match.group(1).strip()
            # If Direct-CPE, we use the physical interface description if available
            router_physical_port = cpe_physical_interface

            # Fallback/Default
        if connectivity_type == 'N/A':
            print(f"  > WARNING: Could not determine L2 binding for BDI {bdi} in {bd_id} output. Set to N/A.")

        # Store initial data
        service_data.append({
            'Router_Hostname': router.hostname,
            'Connectivity_Type': connectivity_type,
            'VRF_Name': vrf_name,
            'Routed_BDI_Interface': bdi,
            'Bridge_Domain_ID': bd_id,
            'Customer_VLAN_ID': service_instance_id if service_instance_id != 'N/A' else 'N/A',
            'Service_L3_IP_Mask': ip_match.group(1).strip() if ip_match else 'N/A',
            'CIR_Kbit_sec': 'N/A',  # To be filled later
            'QoS_Policy_Input': policy_in_match.group(1).strip() if policy_in_match else 'N/A',
            'QoS_Policy_Output': policy_out_match.group(1).strip() if policy_out_match else 'N/A',
            'Interface_Description_Customer_Name': desc_match.group(1).strip() if desc_match else 'N/A',
            'CPE_Physical_Interface_Direct': cpe_physical_interface,
            'Router_Port_Channel_L2': port_channel_name,
            'Router_Uplink_Port_Po_Member': router_physical_port,
            'Last_Mile_Switch_IP': 'N/A',
            'Switch_Uplink_Port_to_Router': 'N/A',
            'Customer_Access_Port_on_Switch': 'N/A',
        })

    # 3. Get Port-channel physical ports and service instance details for Indirect services
    if port_channel_map:
        ether_output = router.send_command("sh etherchannel summary")
        physical_ports = {}
        for po in port_channel_map.keys():
            po_id = po.replace('Port-channel', '')
            # Match the physical port (P) member associated with the Port-channel (Po)
            po_line_match = re.search(rf'^{po_id}\s+{po}\(R[UDS]\)\s+.*?\s+([\w\/\-\.]+)\(P\)', ether_output,
                                      re.MULTILINE)
            physical_ports[po] = po_line_match.group(1) if po_line_match else 'N/A'

        # 4. Get VLAN, Service Policy, and CIR details from Port-Channel Service Instances
        all_po_details = {}

        for po_name in port_channel_map.keys():
            po_run_output = router.send_command(f"sh run int {po_name}")

            service_instance_blocks = re.findall(r'service instance (\d+) ethernet\s+(.*?)(?=service instance|\Z)',
                                                 po_run_output, re.DOTALL)

            for instance_id, block in service_instance_blocks:
                vlan_match = re.search(r'encapsulation dot1q (\d+)', block)
                policy_in_match = re.search(r'service-policy input (\S+)', block)
                policy_out_match = re.search(r'service-policy output (\S+)', block)

                vlan_id = vlan_match.group(1) if vlan_match else 'N/A'
                policy_in_name = policy_in_match.group(1) if policy_in_match else 'N/A'
                policy_out_name = policy_out_match.group(1) if policy_out_match else 'N/A'

                cir = 'N/A'
                policy_to_check = policy_in_name if policy_in_name != 'N/A' else policy_out_name

                # Check policy-map for CIR
                if policy_to_check != 'N/A':
                    policy_output = router.send_command(f"sh policy-map {policy_to_check}")
                    # *** Robust regex for CIR (handles 'cir' or 'rate' and different commands) ***
                    cir_match = re.search(
                        r'(?:police\s+(?:cir|rate)\s+|set\s+bandwidth\s+(\d+)|shape\s+average\s+(\d+))(\d+)\s+',
                        policy_output, re.IGNORECASE)

                    if cir_match:
                        # Get the last captured group which is the rate
                        # Filter out None values and take the last match (the rate value)
                        cir_value_group = [g for g in cir_match.groups() if g is not None][
                            -1] if cir_match.groups() else 'N/A'
                        cir = cir_value_group

                all_po_details[instance_id] = {
                    'Customer_VLAN_ID': vlan_id,
                    'QoS_Policy_Input': policy_in_name,
                    'QoS_Policy_Output': policy_out_name,
                    'CIR_Kbit_sec': cir,
                    'Router_Port_Channel_L2': po_name,
                }

        # 5. Update the service_data list with the fetched Port-channel details
        for item in service_data:
            if item['Connectivity_Type'] == 'Indirect-Switch/L2':
                po_name = item['Router_Port_Channel_L2']
                # The service instance ID should equal the Bridge Domain ID for L2 bridging
                inst_id = item['Bridge_Domain_ID']

                item['Router_Uplink_Port_Po_Member'] = physical_ports.get(po_name, 'N/A')

                if inst_id in all_po_details:
                    # Update fields based on Po Service Instance details
                    po_d = all_po_details[inst_id]
                    item['Customer_VLAN_ID'] = po_d['Customer_VLAN_ID']
                    item['QoS_Policy_Input'] = po_d['QoS_Policy_Input']
                    item['QoS_Policy_Output'] = po_d['QoS_Policy_Output']
                    item['CIR_Kbit_sec'] = po_d['CIR_Kbit_sec']

    # 6. Get Switch IP from ARP table (Only for Indirect-Switch/L2 services)
    router_bdi_ip = 'N/A'
    switch_ip = 'N/A'

    # Try to find the BDI IP of the router in the management VRF
    mgmt_bdi_output = router.send_command(f"sh ip int brief vrf {MGMT_VRF_FOR_ARP}")
    bdi_ip_match = re.search(r'(BDI\d+)\s+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', mgmt_bdi_output)
    if bdi_ip_match:
        router_bdi_ip = bdi_ip_match.group(2).strip()

    if router_bdi_ip != 'N/A':
        # Send ARP command for the management VRF
        arp_output = router.send_command(f"SH IP ARP VRF {MGMT_VRF_FOR_ARP}")

        # Look for the non-router IP that is likely the switch
        for line in arp_output.split('\n'):
            match = re.search(r'Internet\s+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s+\d+\s+\w+\s+\w+', line)
            if match:
                ip_address = match.group(1)
                # Filter out the router's own IP and common non-local/non-switch IPs
                if ip_address != router_bdi_ip and (ip_address.startswith('172.16.') or ip_address.startswith('10.')):
                    switch_ip = ip_address
                    break

    # Add switch IP to all relevant records (Indirect services)
    for item in service_data:
        if item['Connectivity_Type'] == 'Indirect-Switch/L2':
            # Use the derived IP
            item['Last_Mile_Switch_IP'] = switch_ip if switch_ip != 'N/A' else 'N/A'

    return service_data


def extract_switch_details(switch_ip: str, router_data: List[Dict[str, Any]], username, password, secret) -> List[
    Dict[str, Any]]:
    """Connects to the switch and fetches uplink and customer access port details."""

    # Filter out services that are not the Switch/L2 type or don't use this switch IP
    target_data = [d for d in router_data if d['Connectivity_Type'] == 'Indirect-Switch/L2' and (
                d['Last_Mile_Switch_IP'] == switch_ip or d['Last_Mile_Switch_IP'] == 'N/A')]
    if not target_data:
        return router_data

    try:
        print(f"\n--- Connecting to Last Mile Switch ({switch_ip}) for details ---")
        # Use the LiveNetwork class to handle connection and command execution
        with LiveNetwork(switch_ip, username, password, secret, 'cisco_ios') as switch:

            # 1. Get the physical port connecting to the router Po (assuming Po1 on switch is common)
            print(f"[{switch.hostname}] Getting Switch Uplink Port (Po1 Member)...")
            # --- IMPROVEMENT: Increased read_timeout for the switch connection just for stability on the second part ---
            switch.connection.read_timeout = 60

            # --- FIX: We re-try the enable/prompt detection manually if the first attempt fails ---
            if not switch.connection.check_enable_mode():
                switch.connection.enable()

            po1_output = switch.send_command("sh etherchannel summary")
            # Look for the physical port bundled under Po1
            uplink_match = re.search(r'^1\s+Po1\(R[UDS]\)\s+.*?\s+([\w\/\-\.]+)\(P\)', po1_output, re.MULTILINE)
            switch_uplink_port = uplink_match.group(1) if uplink_match else 'Po1'

            # 2. Get customer access ports based on VLANs
            print(f"[{switch.hostname}] Getting Customer Access Ports from VLANs...")
            vlan_port_map = {}
            unique_vlans = {item['Customer_VLAN_ID'] for item in target_data if item['Customer_VLAN_ID'] != 'N/A'}

            for vlan in unique_vlans:
                # Use 'sh vlan brief' for broader compatibility
                vlan_output = switch.send_command(f"sh vlan brief")

                # Regex to find the VLAN line and capture the ports section
                ports_match = re.search(r'^\s*' + str(vlan) + r'\s+.*\s+active\s+(.*)', vlan_output, re.MULTILINE)

                customer_port = 'N/A'
                if ports_match:
                    # Capture the first non-Port-channel, non-Uplink port as the 'customer access port' heuristic
                    port_list_raw = ports_match.group(1).split(',')
                    port_list = [p.strip() for p in port_list_raw if p.strip()]

                    filtered_port_list = [
                        p for p in port_list
                        if not p.startswith('Po') and p != switch_uplink_port
                    ]

                    customer_port = filtered_port_list[0] if filtered_port_list else 'N/A'

                vlan_port_map[vlan] = customer_port

            # 3. Update the router_data with switch details
            for item in router_data:
                if item['Connectivity_Type'] == 'Indirect-Switch/L2' and (
                        item['Last_Mile_Switch_IP'] == switch_ip or item['Last_Mile_Switch_IP'] == 'N/A'):
                    item['Last_Mile_Switch_IP'] = switch_ip
                    item['Switch_Uplink_Port_to_Router'] = switch_uplink_port
                    vlan = item['Customer_VLAN_ID']
                    item['Customer_Access_Port_on_Switch'] = vlan_port_map.get(vlan, 'N/A')

        return router_data

    except Exception as e:
        print(f"\nERROR: Failed to connect or extract data from switch {switch_ip}: {e}")
        # If switch fails, mark the fields in the target data
        for item in router_data:
            if item['Connectivity_Type'] == 'Indirect-Switch/L2' and (
                    item['Last_Mile_Switch_IP'] == switch_ip or item['Last_Mile_Switch_IP'] == 'N/A'):
                item['Last_Mile_Switch_IP'] = switch_ip
                # Keep the requested 'Error Ignored' message, but make sure the switch IP is set
                item['Switch_Uplink_Port_to_Router'] = f'SWITCH CONNECT FAILED (Error Ignored)'
                item['Customer_Access_Port_on_Switch'] = f'SWITCH CONNECT FAILED (Error Ignored)'
        return router_data


# ====================================================================
# MAIN ORCHESTRATOR
# ====================================================================

# Helper function to convert CIR robustly
def convert_to_mbps(x: Any) -> Any:
    """Converts Kbit/s string value to Mbps, handling decimals and N/A values."""
    try:
        # Robustly convert to float first
        val = float(str(x).replace(',', '').strip())
        # Convert Kbit/s to Mbps
        return round(val / 1000, 2)
    except (ValueError, TypeError, AttributeError):
        return x


def main():
    """Main function to run the service discovery script."""

    if 'your_ssh_username' in USERNAME or 'your_ssh_password' in PASSWORD or 'your_enable_secret' in SECRET:
        print("ERROR: Please update the CONFIGURATION & CREDENTIALS section at the top of the script.")
        return

    all_service_data = []
    switch_map = {}

    for target in ROUTER_TARGETS:
        router_ip = target['ip']
        router_hostname = target['hostname']

        # Add the explicit switch hint to the map if it exists
        if target['switch_ip_hint']:
            switch_map[target['switch_ip_hint']] = target['switch_ip_hint']

        try:
            with LiveNetwork(router_ip, USERNAME, PASSWORD, SECRET, 'cisco_ios') as router:

                # --- NEW STEP: Get all configured VRF names using the robust method ---
                vrf_list = get_all_vrf_names(router)

                if not vrf_list:
                    print(
                        f"\n[ROUTER: {router.hostname}] WARNING: Could not retrieve any VRFs. Skipping service check.")
                    continue

                print(f"\n[ROUTER: {router.hostname}] Found {len(vrf_list)} VRFs. Checking for service BDIs...")

                # --- Iterate over ALL discovered VRFs ---
                for vrf in vrf_list:
                    # Filter VRFs using the user's keywords
                    if not any(keyword in vrf.upper() for keyword in TARGET_SERVICE_VRF_KEYWORDS):
                        # print(f"  > Skipping VRF '{vrf}' (no service keyword match).") # Too noisy
                        continue

                    l3_services = extract_l3_services_by_vrf(router, vrf)

                    # If ARP failed, use the hint for all Indirect services on this router
                    for item in l3_services:
                        if item['Connectivity_Type'] == 'Indirect-Switch/L2' and item[
                            'Last_Mile_Switch_IP'] == 'N/A' and target['switch_ip_hint']:
                            item['Last_Mile_Switch_IP'] = target['switch_ip_hint']

                    all_service_data.extend(l3_services)

                # --- Collect ALL Switch IPs for later processing ---
                for item in all_service_data:
                    if item.get('Connectivity_Type') == 'Indirect-Switch/L2' and item.get('Last_Mile_Switch_IP') and \
                            item['Last_Mile_Switch_IP'] != 'N/A' and item['Last_Mile_Switch_IP'] not in switch_map:
                        switch_map[item['Last_Mile_Switch_IP']] = item['Last_Mile_Switch_IP']

        except Exception as e:
            # Mark the router as failed in the final data
            print(f"\nFATAL ERROR processing router {router_hostname} ({router_ip}): {e}")
            all_service_data.append({
                'Router_Hostname': router_hostname,
                'Connectivity_Type': 'ROUTER CONNECT FAILED',
                'VRF_Name': 'N/A',
                'Interface_Description_Customer_Name': f"Connection Error: {e.__class__.__name__}",
                # Fill N/A for all other required fields to maintain DataFrame structure
                'Service_L3_IP_Mask': 'N/A', 'CIR_Kbit_sec': 'N/A', 'Routed_BDI_Interface': 'N/A',
                'Bridge_Domain_ID': 'N/A', 'QoS_Policy_Input': 'N/A', 'QoS_Policy_Output': 'N/A',
                'CPE_Physical_Interface_Direct': 'N/A', 'Router_Port_Channel_L2': 'N/A',
                'Customer_VLAN_ID': 'N/A', 'Router_Uplink_Port_Po_Member': 'N/A',
                'Last_Mile_Switch_IP': 'N/A', 'Switch_Uplink_Port_to_Router': 'N/A',
                'Customer_Access_Port_on_Switch': 'N/A',
            })
            continue

    # --- Post-Processing: Connect to Switches ---
    final_data = all_service_data
    if switch_map:
        for switch_ip in switch_map.keys():
            # Pass all collected data to be updated by the switch details
            # The function handles the failure gracefully by marking the switch columns
            final_data = extract_switch_details(switch_ip, final_data, USERNAME, PASSWORD, SECRET)

    # 4. Data Rephrasing and Consolidation
    print("\n--- Finalizing Data and Creating DataFrame ---")

    df = pd.DataFrame(final_data)

    # --- Robust CIR Conversion ---
    if 'CIR_Kbit_sec' in df.columns:
        df['CIR_Mbps'] = df['CIR_Kbit_sec'].apply(convert_to_mbps)
        df = df.drop(columns=['CIR_Kbit_sec'], errors='ignore')

    # --- Rename columns from internal keys to the final structured keys ---
    RENAME_MAP = {
        'Connectivity_Type': 'Connectivity Type',
        'VRF_Name': 'VRF Name',
        'Routed_BDI_Interface': 'Routed BDI Interface',
        'Bridge_Domain_ID': 'Bridge Domain ID',
        'Customer_VLAN_ID': 'Customer VLAN ID (Po Service)',
        'Service_L3_IP_Mask': 'Service L3 IP/Mask',
        'CIR_Mbps': 'CIR (Mbps)',
        'QoS_Policy_Input': 'QoS Policy (Input)',
        'QoS_Policy_Output': 'QoS Policy (Output)',
        'Interface_Description_Customer_Name': 'Interface Description (Customer Name)',
        'CPE_Physical_Interface_Direct': 'CPE/Physical Interface (Direct)',
        'Router_Port_Channel_L2': 'Router Port-Channel (L2)',
        'Router_Uplink_Port_Po_Member': 'Router Uplink Port (Po Member)',
        'Last_Mile_Switch_IP': 'Last Mile Switch IP',
        'Switch_Uplink_Port_to_Router': 'Switch Uplink Port (to Router)',
        'Customer_Access_Port_on_Switch': 'Customer Access Port (on Switch)',
        'Router_Hostname': 'Router Hostname'
    }

    # Apply renaming to the DataFrame
    df.rename(columns=RENAME_MAP, inplace=True)

    # Define the final column order
    final_columns_order = [
        'Router Hostname', 'Connectivity Type', 'VRF Name',
        'Interface Description (Customer Name)', 'Service L3 IP/Mask', 'CIR (Mbps)',
        'Routed BDI Interface', 'Bridge Domain ID', 'QoS Policy (Input)', 'QoS Policy (Output)',
        'CPE/Physical Interface (Direct)', 'Router Port-Channel (L2)',
        'Customer VLAN ID (Po Service)', 'Router Uplink Port (Po Member)',
        'Last Mile Switch IP', 'Switch Uplink Port (to Router)', 'Customer Access Port (on Switch)',
    ]

    # Reindex and rename columns.
    df_final = df.reindex(columns=final_columns_order, fill_value='N/A')

    # 5. Convert to CSV
    csv_filename = "unified_service_discovery_results.csv"
    df_final.to_csv(csv_filename, index=False)

    print(f"\n--- SUCCESS ---")
    print(f"Data successfully processed for {len(ROUTER_TARGETS)} routers and saved to {csv_filename}")
    print("\nFinal DataFrame Head:")
    print(df_final.head().to_string())


if __name__ == "__main__":
    main()
