# quick_netmiko_collect_with_vrf.py
import pandas as pd
from netmiko import ConnectHandler

hosts = ["172.16.3.49", ]
hostnames = ["HYBDCCSXGPR001",]

# username = "praveen.j"
# password = "Nasa@1021"

username = 'govindareddy.b',
password = 'J!f@b&r&987654',
cmd = "show int description | i Direct"

rows = []
for h, hn in zip(hosts, hostnames):
    dev = {"device_type": "cisco_ios", "host": h, "username": username, "password": password}
    try:
        with ConnectHandler(**dev) as con:
            out = con.send_command(cmd)

            for ln in out.splitlines():
                if not ln.strip():
                    continue
                parts = ln.split()
                if len(parts) >= 4:
                    intf = parts[0]
                    # handle "admin down" as one status
                    if parts[1] == "admin" and parts[2] == "down":
                        status = "admin down"
                        proto = parts[3]
                        desc = " ".join(parts[4:])
                    else:
                        status = parts[1]
                        proto = parts[2]
                        desc = " ".join(parts[3:])
                    desc = desc.strip("#* ")

                    # --- NEW: run show run interface for this interface ---
                    vrf_name = ""
                    try:
                        run_out = con.send_command(f"show run interface {intf}")
                        for line in run_out.splitlines():
                            line = line.strip()
                            if line.startswith("vrf forwarding"):
                                # line looks like: vrf forwarding TDIA-ILL-SPOKE
                                vrf_name = line.split()[-1]
                                break
                    except Exception as e:
                        print(f"Could not get VRF for {hn}:{intf} -> {e}")

                    rows.append({
                        "hostname": hn,
                        "host_ip": h,
                        "interface": intf,
                        "status": status,
                        "protocol": proto,
                        "description": desc,
                        "vrf": vrf_name
                    })

    except Exception as e:
        print(f"Failed {h} ({hn}): {e}")
        continue

df = pd.DataFrame(rows, columns=["hostname", "host_ip", "interface", "status", "protocol", "description", "vrf"])
print(df.to_string(index=False))
# df.to_csv(r"E:\PycharmProjects\ServiceDiscoveryMain\IPReports\IPMPLSServiceDiscovery.csv", index=False)
# print("Saved IPMPLSServiceDiscovery.csv")
