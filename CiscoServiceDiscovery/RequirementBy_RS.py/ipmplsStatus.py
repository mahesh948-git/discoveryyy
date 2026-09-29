import paramiko
import time
import pandas as pd

devices = [
    {"hostname": "NOCTESTMAR001", "ip": "172.17.224.1","System Location":"TNOC-TESTLAB1" ,"LGDCode":"1234" ,},
    {"hostname":"NOCTESTMAR002","ip":"172.17.224.2","System Location":"TNOC-TESTLAB2","LGDCode":"1234"}
]

# username = "praveen.j"
# password = "Nasa@1021"
username = 'govindareddy.b',
password = 'J!f@b&r&987654',

commands = [
    "conf t",
    "snmp-server location TESTLAB-TNOC",
    "snmp-server contact LGD9999",
    "exit",
    "wr"
]

results = []

def configure_device(hostname, ip):

    status = "SUCCESS"

    try:
        print(f"\nConnecting to {hostname} ({ip})")

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        ssh.connect(
            hostname=ip,
            username=username,
            password=password,
            timeout=20
        )

        shell = ssh.invoke_shell()

        time.sleep(2)

        if shell.recv_ready():
            print(shell.recv(65535).decode())

        for cmd in commands:

            print(f"Executing: {cmd}")

            shell.send(cmd + "\n")

            if cmd == "wr":
                time.sleep(10)
            else:
                time.sleep(2)

            if shell.recv_ready():
                output = shell.recv(65535).decode()
                print(output)

        ssh.close()

    except Exception as e:
        status = f"FAILED - {str(e)}"
        print(status)

    # Store result
    results.append({
        "Host": ip,
        "Hostname": hostname,
        "Status": status
    })


# --------------------------------
# MAIN
# --------------------------------
for device in devices:
    configure_device(device["hostname"], device["ip"])

# --------------------------------
# EXPORT TO EXCEL
# --------------------------------
df = pd.DataFrame(results)

output_file = "device_status.csv"

df.to_csv(output_file, index=False)

print(f"\nCSV report generated: {output_file}")