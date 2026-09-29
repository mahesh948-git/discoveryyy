import paramiko
import time
import pandas as pd
import subprocess


input_file = "Switch-List 12-May-26.csv"

# Read excel
devices_df = pd.read_csv(input_file)

# username = "praveen.j"
# password = "Nasa@1021"
username = 'govindareddy.b',
password = 'J!f@b&r&987654',

results = []

def ping_device(ip):

    try:
        # Windows ping command
        result = subprocess.run(
            ["ping", "-n", "2", ip],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            return True
        else:
            return False

    except Exception:
        return False


# --------------------------------
# CONFIGURE DEVICE FUNCTION
# --------------------------------
def configure_device(hostname, ip, location, lgdcode):

    status = "SUCCESS"

    print(f"\nPinging {hostname} ({ip})")

    ping_status = ping_device(ip)

    if not ping_status:

        print(f"{ip} is not reachable")

        results.append({
            "Name": hostname,
            "Management Address": ip,
            "System Location": location,
            "LGD Code": lgdcode,
            "Ping Status": "FAILED",
        })

        return

    print(f"{ip} reachable")

    try:

        ssh = paramiko.SSHClient()

        ssh.set_missing_host_key_policy(
            paramiko.AutoAddPolicy()
        )

        ssh.connect(
            hostname=ip,
            username=username,
            password=password,
            timeout=20
        )

        shell = ssh.invoke_shell()

        time.sleep(2)

        commands = [
            "conf t",
            f"snmp-server location {location}",
            f"snmp-server contact {lgdcode}",
            "exit",
            "wr"
        ]
       
        # EXECUTE COMMANDS
        for cmd in commands:

            print(f"Executing: {cmd}")

            shell.send(cmd + "\n")

            # wr takes more time
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

    results.append({
        "Name": hostname,
        "Management Address": ip,
        "System Location": location,
        "LGD Code": lgdcode,
        "Ping Status": "SUCCESS",
    })


# --------------------------------
# LOOP THROUGH EXCEL DEVICES
# --------------------------------
for index, row in devices_df.iterrows():

    hostname = str(row["Name"]).strip()
    ip = str(row["Management Address"]).strip()
    location = str(row["System Location"]).strip()
    lgdcode = str(row["LGD Code"]).strip()

    configure_device(
        hostname,
        ip,
        location,
        lgdcode
    )

# --------------------------------
# EXPORT CSV REPORT
# --------------------------------
output_file = "switches_output_may_12.csv"

results_df = pd.DataFrame(results)

results_df.to_csv(output_file, index=False)

print(f"\nCSV report generated: {output_file}")