# quick_netmiko_collect_fixed3.py
import pandas as pd
from netmiko import ConnectHandler

hosts = ["172.16.3.47","172.16.3.49", "172.16.3.58","172.16.80.225", "172.16.80.227", 
         "172.16.6.51","10.253.192.131","172.16.3.48","172.16.6.64","172.16.0.184"]
hostnames = ["RRDSHAMXGPR001","HYBDCCSXGPR001", "HYDSRNIDGPR001", "HYDTGSECMAR001", "HYBDGAPSMAG001", 
             "GACHCPCOGPR001","KBAJNORXMAR001","RRRRJNRXGPR001","HYDBRAIGGP001","SECURASOGPR001"]

# username = "praveen.j"
# password = "Nasa@1021"
username = 'govindareddy.b',
password = 'J!f@b&r&987654',
cmd = "show int description | i Direct"
# cmd = "show int description"

rows = []
for h, hn in zip(hosts, hostnames):
    dev = {"device_type": "cisco_ios", "host": h, "username": username, "password": password}
    try:
        with ConnectHandler(**dev) as con:
            out = con.send_command(cmd)
    except Exception as e:
        print(f"Failed {h} ({hn}): {e}")
        continue

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
            if status.lower() in ["up"]:
                status = "UP"
            elif "down" in status.lower():
                status = "DOWN"
            else:
                status = status.upper()
            desc = desc.strip("#* ")
            rows.append({
                "hostname": hn,
                "host_ip": h,
                "interface": intf,
                "status": status,
                "protocol": proto,
                "description": desc
            })

df = pd.DataFrame(rows, columns=["hostname", "host_ip", "interface", "status", "protocol", "description"])
print(df.to_string(index=False))
df.to_csv("IPMPLSServiceDiscovery_here.csv", index=False)
# df.to_csv("IPMPLSServiceDiscovery_here_new.csv", index=False)

# df.to_csv("E:\PycharmProjects\ServiceDiscoveryMain\IPReports\IPMPLSServiceDiscovery.csv", index=False)
# print("Saved interfaces_direct.csv")
