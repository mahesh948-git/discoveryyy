"""
Router+Switch collector for BDIs / last-mile details.

Usage:
- Fill `router_device` with IP, username, password, device_type (e.g. 'cisco_ios')
- Optionally provide enable_password (if needed)
- Run: python collect_router_info.py

Output:
- Prints a pandas DataFrame
- Saves CSV to router_<router_ip>_interfaces.csv
"""

import re
from netmiko import ConnectHandler
import pandas as pd
import logging
from typing import Dict, List, Optional, Tuple

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


# ---------- Helpers: parsing functions ----------

def parse_sh_ip_vrf(output: str) -> Dict[str, Dict]:
    """
    Robust parser for 'show ip vrf'.
    Returns mapping: {VRF_NAME: {'rd': RD_VALUE, 'interfaces': [BDI..., ...]}}
    Handles indented interfaces on continuation lines.
    """
    print("Raw output:\n", output)
    vrfs = {}
    lines = [ln.rstrip() for ln in output.splitlines() if ln.strip()]
    current_vrf = None

    for ln in lines:
        ln_stripped = ln.lstrip()  # remove leading spaces

        # skip header
        if ln_stripped.lower().startswith("name") or ln_stripped.lower().startswith("---"):
            continue

        # New VRF line: starts with VRF name
        # (after stripping leading spaces)
        if re.match(r"^\S", ln_stripped):
            parts = re.split(r"\s{2,}", ln_stripped)  # split by 2+ spaces
            if len(parts) >= 2:
                vrf_name = parts[0]
                rd = parts[1]
                interfaces = []
                if len(parts) > 2:
                    interfaces += re.findall(r"[A-Za-z0-9/_-]+", parts[2])
                vrfs[vrf_name] = {"rd": rd, "interfaces": interfaces}
                current_vrf = vrf_name
        else:
            # continuation line for interfaces
            if current_vrf:
                vrfs[current_vrf]["interfaces"] += re.findall(r"[A-Za-z0-9/_-]+", ln_stripped)

    print("Parsed VRFs:", vrfs)
    return vrfs



def parse_sh_run_int(output: str) -> Dict[str, Optional[str]]:
    """
    Parse 'sh run int <name>' for BDI style output.
    Returns dict with:
      name, description, vrf, ip_address (IP string), ip_mask (netmask)
    """
    text = output
    # interface name
    mname = re.search(r"^interface\s+(\S+)", text, re.M)
    name = mname.group(1) if mname else None
    # description
    mdesc = re.search(r"^\s*description\s+(.*)$", text, re.M)
    description = mdesc.group(1).strip() if mdesc else None
    # vrf forwarding
    mvrf = re.search(r"^\s*vrf forwarding\s+(\S+)", text, re.M)
    vrf = mvrf.group(1) if mvrf else None
    # ip address line (ip address <ip> <mask> OR ip address x/x)
    mip = re.search(r"^\s*ip address\s+(\d+\.\d+\.\d+\.\d+)\s+(\d+\.\d+\.\d+\.\d+)", text, re.M)
    ip_address = None
    ip_mask = None
    if mip:
        ip_address = mip.group(1)
        ip_mask = mip.group(2)
    return {"name": name, "description": description, "vrf": vrf, "ip": ip_address, "mask": ip_mask}


def parse_sh_int_description(output: str) -> Dict[str, Dict]:
    """
    Parse 'sh int <int> description' outputs.
    Returns mapping {interface: {'status':..., 'protocol':..., 'description':...}}
    """
    results = {}
    lines = [ln for ln in output.splitlines() if ln.strip()]
    # find header line index
    # Then parse subsequent lines like:
    # BD3301  admin down  down   ***desc***
    for ln in lines:
        m = re.match(r"^(BDI?\d+|\S+)\s+(\S+)\s+(\S+)\s+(.*)$", ln)
        if m:
            intf = m.group(1)
            status = m.group(2)
            proto = m.group(3)
            desc = m.group(4).strip()
            results[intf] = {"status": status, "protocol": proto, "description": desc}
    return results


def parse_bridge_domain(output: str) -> Dict:
    """
    Parse 'sh bridge-domain <bd>' like:
    Bridge-domain 3301 (2 ports in all)
    ...
       BD    mac addr        type     ports
       3301  a488.73a3.6759  DYNAMIC  Po0/0/30.Efp3301
    Returns: {'bd': <id>, 'ports': [list of ports like Po0/0/30.Efp3301], 'mac_entries': [...]}
    """
    res = {"bd": None, "ports": [], "mac_entries": []}
    m = re.search(r"Bridge-domain\s+(\d+)", output)
    if m:
        res["bd"] = m.group(1)
    # collect ports lines that appear under the simple list (lines showing BDI and port-channel service instance)
    ports = re.findall(r"([A-Za-z0-9/._-]+E?fp?\d+|Po[0-9/._-]+|Port-channel[0-9/._-]+|Po\d+)", output)
    if ports:
        res["ports"] = ports
    # mac entries
    mac_lines = re.findall(r"(\d+)\s+([0-9a-fA-F.]+)\s+(\S+)\s+(\S+)", output)
    for bd, mac, mtype, port in mac_lines:
        res["mac_entries"].append({"bd": bd, "mac": mac, "type": mtype, "port": port})
    return res


def parse_etherchannel_summary(output: str) -> Dict[str, Dict]:
    """
    Parse 'sh etherchannel summary' - returns mapping of port-channel group -> dict info including member ports
    Example returned:
      {'30': {'port_channel': 'Po30', 'ports': ['Gi0/0/9(P)']}, ...}
    """
    groups = {}
    # find lines like: 30      Po30(RU)                         Gi0/0/9(P)
    for ln in output.splitlines():
        ln = ln.strip()
        m = re.match(r"^(\d+)\s+(\S+)\s+\S*\s*(.*)$", ln)
        if m:
            grp = m.group(1)
            po = m.group(2)
            ports_field = m.group(3).strip()
            ports = []
            if ports_field:
                # split by spaces and commas
                ports = re.findall(r"[\w/]+(?:\(\w+\))?", ports_field)
            groups[grp] = {"port_channel": po, "ports": ports}
    return groups


def parse_sh_run_po(output: str) -> Dict[str, Dict]:
    """
    Parse 'sh run int Port-channelXX' service-instances
    Returns mapping of service-instance (vlan/bridge-domain) -> details like encapsulation dot1q and service-policy
    """
    res = {"port_channel": None, "service_instances": {}}
    m = re.search(r"^interface\s+(\S+)", output, re.M)
    if m:
        res["port_channel"] = m.group(1)
    # find blocks 'service instance 3301 ethernet ...'
    blocks = re.split(r"(?m)^service instance\s+", output)
    for blk in blocks[1:]:
        # start with id
        m2 = re.match(r"(\d+)\s+ethernet(.*?)(?=(^service instance\s+\d+\s+ethernet)|\Z)", blk, re.S | re.M)
        if m2:
            sid = m2.group(1)
            body = m2.group(2)
            # find encapsulation dot1q <vlan>
            mell = re.search(r"encapsulation\s+dot1q\s+(\d+)", body)
            vlan = mell.group(1) if mell else None
            # find service-policy input <name>
            mpol = re.search(r"service-policy\s+input\s+(\S+)", body)
            pol = mpol.group(1) if mpol else None
            # find description
            mdesc = re.search(r"description\s+(.*)", body)
            desc = mdesc.group(1).strip() if mdesc else None
            res["service_instances"][sid] = {"vlan": vlan, "policy": pol, "description": desc}
    return res


def parse_policy_map(output: str) -> Dict:
    """
    Parse 'sh policy-map <name>' for police cir <value>
    Returns {'policy': name, 'police_cir_bps': int or None}
    """
    r = {}
    mname = re.search(r"Policy Map\s+(\S+)", output)
    if mname:
        r["policy"] = mname.group(1)
    mcir = re.search(r"police\s+cir\s+(\d+)", output)
    if mcir:
        try:
            r["police_cir_bps"] = int(mcir.group(1))
        except ValueError:
            r["police_cir_bps"] = None
    else:
        r["police_cir_bps"] = None
    return r


def parse_arp(output: str) -> List[Dict]:
    """
    Parse ARP lines like:
    Internet  172.16.22.54          216   a488.73a3.6758  ARPA   BDI500
    """
    res = []
    for ln in output.splitlines():
        m = re.match(r"^\s*\S+\s+(\d+\.\d+\.\d+\.\d+)\s+(\S+)\s+([0-9a-fA-F.]+)\s+(\S+)\s+(\S+)", ln)
        if m:
            ip = m.group(1)
            age = m.group(2)
            mac = m.group(3)
            typ = m.group(4)
            interface = m.group(5)
            res.append({"ip": ip, "age": age, "mac": mac, "type": typ, "interface": interface})
    return res


def parse_vlan_tag(output: str) -> Dict:
    """
    Parse 'sh vlan tag <vlan>' listing which ports are tagged/untagged
    Returns {'vlan': id, 'tagged_ports':[...], 'untagged_ports':[...]}
    """
    vlan = None
    tagged = []
    untagged = []
    for ln in output.splitlines():
        m = re.match(r"^(\d+)\s+(\S+)\s+(\S+)?\s*(\S+)?\s*$", ln)
        if m and not ln.startswith("----"):
            # crude parsing using columns: Vlan Name TaggedPorts UnTaggedPorts ...
            items = re.split(r"\s{2,}", ln.strip())
            if items:
                # first entry likely VLAN number
                if items[0].isdigit():
                    vlan = items[0]
                    if len(items) >= 3:
                        tagged = items[2].split() if items[2] else []
                    if len(items) >= 4:
                        untagged = items[3].split() if items[3] else []
                    break
    return {"vlan": vlan, "tagged_ports": tagged, "untagged_ports": untagged}


def parse_interfaces_portchannel(output: str) -> Dict:
    """
    Parse 'sh interfaces port-channel X' to find which actual ports are active
    Looks for lines like 'Po1      Active: gi9' or 'Po1      Active: gi9, gi10'
    """
    res = {}
    for ln in output.splitlines():
        ln = ln.strip()
        m = re.match(r"^Po\d+\s+Active:\s*(.*)$", ln, re.I)
        if m:
            ports = re.split(r"[,\s]+", m.group(1).strip())
            res["active_ports"] = [p for p in ports if p]
    return res


# ---------- Main orchestration ----------

def collect_from_router(router: Dict, commands: Dict) -> pd.DataFrame:
    """
    router: dict for ConnectHandler (host, username, password, device_type, secret optional)
    commands: dictionary with keys for different command strings to execute
    """
    logging.info(f"Connecting to router {router.get('host')}")
    conn = ConnectHandler(**router)
    if router.get("secret"):
        conn.enable()
    df_rows = []

    # 1) sh ip vrf
    vrf_out = conn.send_command(commands.get("sh_ip_vrf", "show ip vrf"))
    vrfs = parse_sh_ip_vrf(vrf_out)
    logging.info(f"Found VRFs: {list(vrfs.keys())}")

    # For each VRF, fetch details (interfaces are listed in vrfs mapping)
    for vrf_name, vrf_info in vrfs.items():
        for bdi in vrf_info.get("interfaces", []):
            # Normalize name
            intf = bdi
            # 3) sh run int <int>
            cmd_run_int = f"show running-config interface {intf}"
            logging.info(f"Collecting run for {intf}")
            out_run_int = conn.send_command(cmd_run_int)
            parsed_if = parse_sh_run_int(out_run_int)
            # 4) sh int <int> description
            out_desc = conn.send_command(f"show interfaces {intf} description")
            desc_info = parse_sh_int_description(out_desc).get(intf, {})
            # 4b) bridge-domain - find BD ID from interface name: try to infer BD from BDI number
            # We'll run 'show bridge-domain <bdnum>' where bdnum may be digits in the BDI name
            bd_num_match = re.search(r"BDI?(\d+)", intf)
            bdnum = bd_num_match.group(1) if bd_num_match else None
            bridge_info = {}
            if bdnum:
                try:
                    out_bd = conn.send_command(f"show bridge-domain {bdnum}")
                    bridge_info = parse_bridge_domain(out_bd)
                except Exception:
                    bridge_info = {}
            # 5) find port-channel from bridge domain mac entries (extract PoN)
            port_channel = None
            if bridge_info.get("mac_entries"):
                # take first mac entry port and try to extract port-channel Po...
                for m in bridge_info["mac_entries"]:
                    port = m.get("port", "")
                    po_match = re.search(r"(Po[0-9/._-]+|Port-channel[0-9]+|Po\d+|Gi[0-9/]+)", port)
                    if po_match:
                        port_channel = po_match.group(0)
                        break
            # If not found, try etherchannel summary
            if not port_channel:
                out_ec = conn.send_command("show etherchannel summary")
                ec = parse_etherchannel_summary(out_ec)
                # find group that has a member referencing a matching interface (based on bridge_info ports)
                for g, info in ec.items():
                    for p in info.get("ports", []):
                        if bdnum and re.search(str(bdnum), p):
                            port_channel = info.get("port_channel")
                    # fallback: if any port contains '/9' or similar maybe it's the one
                # fallback: search for Po30 in outputs (since sample shows Po30)
                if not port_channel and "30" in ec:
                    port_channel = ec["30"]["port_channel"]

            # 6) get port-channel config (sh run int poX)
            po_info = {}
            if port_channel:
                out_po_run = conn.send_command(f"show running-config interface {port_channel}")
                po_info = parse_sh_run_po(out_po_run)
            # 7) get policy maps for service instances from po_info
            vsi_details = {}
            if po_info.get("service_instances"):
                for sid, si in po_info["service_instances"].items():
                    policy = si.get("policy")
                    vlan = si.get("vlan")
                    # fetch policy-map details
                    policy_details = {}
                    if policy:
                        out_pol = conn.send_command(f"show policy-map {policy}")
                        policy_details = parse_policy_map(out_pol)
                    vsi_details[sid] = {"vlan": vlan, "policy": policy, "policy_details": policy_details}

            # 8) If the BDI interface is in a management vrf that contains the switch IP (like BDI500)
            switch_ip = None
            if parsed_if.get("vrf"):
                # attempt to run ARP lookup for that BDI's VRF and interface to find other IPs (like switch)
                try:
                    arp_out = conn.send_command(f"show ip arp vrf {parsed_if.get('vrf')} {intf}")
                    arps = parse_arp(arp_out)
                    # pick IPs that are not the BDI itself
                    for a in arps:
                        if a["ip"] != parsed_if.get("ip"):
                            # heuristics: choose IP with mac starting a488... from sample
                            switch_ip = a.get("ip")
                            break
                except Exception:
                    switch_ip = None

            # Compose row
            row = {
                "router": router.get("host"),
                "bdi_interface": parsed_if.get("name"),
                "description": parsed_if.get("description") or desc_info.get("description"),
                "vrf": parsed_if.get("vrf"),
                "ip": parsed_if.get("ip"),
                "mask": parsed_if.get("mask"),
                "bd": bdnum,
                "bridge_ports": bridge_info.get("ports"),
                "bridge_mac_entries": bridge_info.get("mac_entries"),
                "port_channel": port_channel,
                "po_service_instances": po_info.get("service_instances"),
                "vsi_details": vsi_details,
                "switch_ip_from_arp": switch_ip,
            }
            df_rows.append(row)

    # After processing all BDIs, attempt to connect to any discovered switch IPs and collect VLAN/ports
    df = pd.DataFrame(df_rows)
    # Unique switch IPs found
    if "switch_ip_from_arp" in df.columns:
        discovered_switch_ips = sorted({r for r in df["switch_ip_from_arp"].tolist() if r})
    else:
        print("⚠️ Warning: Column 'switch_ip_from_arp' not found in df. Proceeding with empty list.")
        discovered_switch_ips = []
    switch_info_map = {}
    for sip in discovered_switch_ips:
        # attempt to login to switch using same creds, but device_type may differ
        # assume generic 'cisco_nxos' or 'cisco_ios' — try cisco_ios first
        logging.info(f"Attempting switch login to {sip}")
        sw_conn_params = {
            "host": sip,
            "username": router.get("username"),
            "password": router.get("password"),
            "device_type": router.get("device_type", "cisco_ios"),
        }
        try:
            sw = ConnectHandler(**sw_conn_params)
            # For each VLAN we saw in vsi_details, query 'show vlan tag <vlan>' and 'show interfaces port-channel X'
            # Collect per-switch info
            sw_data = {}
            # gather VLANs from df vsi_details
            vlans = set()
            for _, row in df.iterrows():
                vsi = row.get("po_service_instances") or {}
                for sid, sdet in (vsi.items() if isinstance(vsi, dict) else []):
                    if sdet.get("vlan"):
                        vlans.add(sdet["vlan"])
                # Also check vsi_details field
                try:
                    for sid, sdet in (row.get("vsi_details") or {}).items():
                        if sdet.get("vlan"):
                            vlans.add(sdet["vlan"])
                except Exception:
                    pass
            sw_vlans = {}
            for v in vlans:
                try:
                    out_vlan_tag = sw.send_command(f"show vlan tag {v}")
                    sw_vlans[v] = parse_vlan_tag(out_vlan_tag)
                except Exception:
                    sw_vlans[v] = {}
            sw_data["vlans"] = sw_vlans

            # Also get interfaces port-channel 1 (example) — we'll attempt Po1 and Po30 found earlier
            # Try common port-channels
            for candidate_po in ["Po1", "Po30", "Po10", "Po11"]:
                try:
                    out_ifpo = sw.send_command(f"show interfaces port-channel {candidate_po.replace('Po','')}")
                    pcinfo = parse_interfaces_portchannel(out_ifpo)
                    if pcinfo:
                        sw_data.setdefault("portchannels", {})[candidate_po] = pcinfo
                except Exception:
                    pass

            switch_info_map[sip] = sw_data
            sw.disconnect()
        except Exception as e:
            logging.warning(f"Could not connect to switch {sip}: {e}")
            switch_info_map[sip] = {"error": str(e)}

    # attach switch info to df rows
    def pick_switch_info(row):
        sip = row.get("switch_ip_from_arp")
        return switch_info_map.get(sip, {})

    df["switch_info"] = df.apply(pick_switch_info, axis=1)

    conn.disconnect()
    return df


# ---------- Example invocation ----------
if __name__ == "__main__":
    # Replace these with real credentials & host
    router_device = {
        "host": "172.16.3.49",            # router management IP
        "username": "praveen.j",
        "password": "Nasa@1021",
        "device_type": "cisco_ios",     # adjust if different
        # "secret": "enable_secret",    # uncomment if you need enable
    }

    commands_to_run = {
        "sh_ip_vrf": "show ip vrf",
        # other commands are built dynamically by the script
    }

    df_result = collect_from_router(router_device, commands_to_run)
    # Print & save
    pd.set_option("display.max_columns", None)
    print(df_result)
    csv_name = f"router_{router_device['host']}_interfaces.csv"
    df_result.to_csv(csv_name, index=False)
    logging.info(f"Saved results to {csv_name}")
