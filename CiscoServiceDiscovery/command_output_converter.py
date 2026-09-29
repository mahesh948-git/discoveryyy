##### convert whole router info command : sh vrf
def vrf_converter(vrf_output, ip):
    try:
        vrf_lines = [item.strip() for item in vrf_output.splitlines() if 'Platform' not in item and item.strip() != '' and '<not set>' not in item][1:]
        vrf_dict = []
        for vrf in vrf_lines:
            individual_vrf = [item for item in vrf.split(' ') if item not in '']
            individual_vrf = [item for item in individual_vrf if item.lower() not in ['ipv4,ipv6', 'ipv4', 'ipv6']]
            if len(vrf) > 10:
                if len(individual_vrf) == 3:
                    vrf_dict.append({
                        'service_name': individual_vrf[0],
                        'Default RD': individual_vrf[1],
                        'Interfaces': [individual_vrf[2]]
                    })
                else:
                    vrf_dict.append({
                        'service_name': individual_vrf[0],
                        'Default RD': individual_vrf[1],
                        'Interfaces': []
                    })
            else:
                vrf_dict[-1]['Interfaces'].append(individual_vrf[0])
        return vrf_dict
    except Exception as e:
        print(f'Error in fetching vrf: {e} at ip: {ip}')
        return []


##### each port-channel command: sh bridge-domain <3303>
def port_channel_finder_with_bd(port_channel_output, ip):
    try:
        port_channel_lines = [item.strip().split()[0] for item in port_channel_output.splitlines() if 'service instance' in item]
        if port_channel_lines:
            return ', '.join(port_channel_lines)
        else:
            return None
    except Exception as e:
        print(f'Error in fetching port_channel: {e} at ip: {ip}')
        return None

##### converts whole output command : show inventory
def chassis_info_converter(chassis_info_output, ip):
    try:
        chassis_info_lines = [[item, chassis_info_output.splitlines()[index+1]] for index, item in enumerate(chassis_info_output.splitlines()) if 'NAME: "Chassis"' in item][0]
        try:
            router_model = chassis_info_lines[0].split(' DESCR:')[-1].strip()[1:-1].split('-')[0].strip()
        except:
            router_model = None
        try:
            router_serial = chassis_info_lines[1].split('SN:')[-1].strip()
        except:
            router_serial = None
        if chassis_info_lines:
            return { 'Router Model' : router_model, 'Router Serial No': router_serial }
        else:
            return {'Router Model' : None, 'Router Serial No': None}
    except Exception as e:
        print(f'Error in fetching chassis: {e} of ip: {ip}')
        return {'Router Model' : None, 'Router Serial No': None}

##### whole output command : show running-config | include hostname
def hostname_converter(hostname_output, ip):
    try:
        hostname_lines = [item for item in hostname_output.splitlines() if 'hostname' in item]
        if hostname_lines:
            try :
                return hostname_lines[0].split(' ')[-1]
            except:
                return None
        else:
            return None
    except Exception as e:
        print(f'Error in fetching hostname: {e} at ip: {ip}')
        return str(e)

#### each output ... command : show run vrf <GI_BB_SERVICES>
def l3vpn_converter(l3vpn_type_output):
    try:
        l3vpn_type_lines = list(set([item.strip() for item in l3vpn_type_output.splitlines() if 'route-target export' in item or 'route-target import' in item ]))
        try:
            import_rt = [item for item in l3vpn_type_lines if 'route-target import' in item]
        except:
            import_rt = None
        try:
            export_rt = [item for item in l3vpn_type_lines if 'route-target export' in item]
        except:
            export_rt = None
        if len(l3vpn_type_lines) == 2:
            return { 'L3VPN Type' : 'Full Mesh', 'L3VPN Import RT': import_rt, 'L3VPN Export RT': export_rt, }
        else:
            return { 'L3VPN Type' : 'HUB & Spoke', 'L3VPN Import RT': import_rt, 'L3VPN Export RT': export_rt, }
    except Exception as e:
        print(f'Error in fetching l3vpn_type: {e}')
        return { 'L3VPN Type' : None, 'L3VPN Import RT': None, 'L3VPN Export RT': None, }

### each port-channel info command: show int <port-channel41>
def port_channel_info(port_channel_output, ip):
    try:
        port_channel_lines = [item.strip() for item in port_channel_output.splitlines() if item != '' and 'line protocol' in item or 'Member' in item]
        try:
            line_status = port_channel_lines[0].split(',')[-1].split(' ')[-1]
        except:
            line_status = None
        try:
            physical_bound = [item.split(":")[-1].split(',')[0] for item in port_channel_lines if 'GigabitEthernet' in item]
        except:
            physical_bound = None
        try:
            port_status = port_channel_lines[0].split(',')[0].split(' ')[-1]
        except:
            port_status = None

        return { 'Port-channel Status': port_status, 'Line-protocol Status': line_status, 'Physical interface status bound to BD': physical_bound }
    except Exception as e:
        print(f'Error in fetching port-channel info: {e} at ip:{ip}')
        return { 'Port-channel Status': None, 'Line-protocol Status': None, 'Physical interface status bound to BD': None }


### each BDI info command: show int <BDI500>
def bridge_domain_info(bridge_domain_output):
    try:
        bridge_domain_lines = [item.strip() for item in bridge_domain_output.splitlines() if item != '']
        bridge_status = [item for item in bridge_domain_lines if 'line protocol' in item]
        bd_description = next((item.split(':')[-1].strip().replace('#', '').strip() for item in bridge_domain_lines if 'Description' in item), None)
        traffic_status_on_bdi = [item for item in bridge_domain_lines if 'input rate' in item or 'output rate' in item]
        try:
            bd_status = bridge_status[0].split(',')[0].split(' ')[-1]
        except:
            bd_status = None
        try:
            line_status = bridge_status[0].split(',')[-1].split(' ')[-1]
        except:
            line_status = None
        return {'BDI status': bd_status, 'Line-protocol Status': line_status, 'Description': bd_description, 'Input Traffic status on BDI': traffic_status_on_bdi[0] if traffic_status_on_bdi else None, 'Output Traffic status on BDI': traffic_status_on_bdi[1] if traffic_status_on_bdi else None, }
    except Exception as e:
        print(f'Error in fetching BDI info: {e}')
        return { 'BDI status': None, 'Line-protocol Status': None, 'Description': None, 'Input Traffic status on BDI': None, 'Output Traffic status on BDI': None, }


def port_channel_run_interface_info(port_channel_run_output, ip):
    try:
        port_channel_run_lines = [item.strip() for item in port_channel_run_output.splitlines() if item != '']

        # Extract the interface description (safely)
        interface_description = [[port_channel_run_lines[index], port_channel_run_lines[index + 1]]
                                 for index, item in enumerate(port_channel_run_lines) if 'interface' in item]

        if interface_description:
            interface = interface_description[0][0].split("interface")[-1].strip()
            description = interface_description[0][-1].split('description')[-1].replace("#", '').strip()
        else:
            interface = None
            description = None

        services = []
        first_index_of_service_instance = next(
            (i for i, element in enumerate(port_channel_run_lines) if 'service instance' in element), None)

        if first_index_of_service_instance is not None:
            all_service_interfaces = [item for item in port_channel_run_lines[first_index_of_service_instance:]]
            indices = [i for i, x in enumerate(all_service_interfaces) if x == "!"]
            all_service_interfaces_sublist = [all_service_interfaces[i + 1:j] for i, j in
                                              zip([-1] + indices, indices + [len(all_service_interfaces)])][:-1]

            for service in all_service_interfaces_sublist:
                services.append({
                    'VLAN': next((item.split(' ')[-1] for item in service if 'encapsulation' in item), None),
                    'description': next((item.split('description')[-1].strip().replace('#', '').replace('*', '').strip()
                                         for item in service if 'description' in item), None),
                    'encapsulation': next((item.split(' ')[-2] for item in service if 'encapsulation' in item), None),
                    'Service Policy Input': next(
                        (item.split('input')[-1] for item in service if 'service-policy input' in item), None),
                    'Bridge Domain': next(
                        (item.split('bridge-domain')[-1].strip() for item in service if 'bridge-domain' in item), None)
                })

        return {'Interface': interface, 'Description': description, 'Service Instances': services}

    except Exception as e:
        # Log error with the IP address and return a dictionary with error values
        print(f'Error in fetching run port-channel Info: {e} at ip: {ip}')
        return {'Interface': None, 'Description': None, 'Service Instances': None}


#### whole output ... command : sho cdp nei
def cdp_neighbours_info(cdp_neighbours_output):
    try:
        cdp_neighbours_info_lines = [item.strip() for item in cdp_neighbours_output.splitlines() if item != '']
        all_cdps = [[cdp_neighbours_info_lines[index], [item for item in cdp_neighbours_info_lines[index+1].split(' ') if '' != item] ] for index, item in enumerate(cdp_neighbours_info_lines) if 'tfiber.in' in item]
        total_cdps = len(all_cdps)
        cdps = []
        for single_cdp in all_cdps:
            if len(single_cdp[1]) == 8:
                cdps.append({
                        'Device ID': single_cdp[0].split('.')[0].strip(),
                        'Local Interface Port': f"Ten {single_cdp[1][1]}",
                        'Model': single_cdp[1][-3],
                        'End Point Interface Port': f"Ten {single_cdp[1][-1]}"
                    })
            else:
                cdps.append({
                        'Device ID': single_cdp[0].split('.')[0].strip(),
                        'Local Interface Port': f"Ten {single_cdp[1][1]}",
                        'Model': single_cdp[1][-2],
                        'End Point Interface Port': f"{single_cdp[1][-1]}"
                    })
        return {'Total Cdps': total_cdps, 'CDPs Information': cdps}
    except Exception as e:
        print(f'Error in fetching run CDP neighbour Info: {e}')
        return {'Total Cdps': e, 'CDPs Information': e}

#### whole output ... command : sho arp vrf  TFIBER-IP-MGMT | inc 101
def olt_bd_info_finder(bd_output):
    try:
        bd_ports_olt = [item.strip().split(' ')[0] for item in bd_output.splitlines()]
        bd_ports_olt = [i for i in bd_ports_olt if 'BD' in i]
        return bd_ports_olt
    except Exception as e:
        print(f'Error in fetching olt_bd_info_finder: {e}')
        return []


def connected_olt_ip(olt_output, bridge_domain):
    try:
        olt_ip_lines = [item.strip().split('  ')[1:2][0] for item in olt_output.splitlines()]
        if olt_ip_lines:
            return {bridge_domain: olt_ip_lines[1:]}
        else:
            return {bridge_domain: []}
    except Exception as e:
        print(f'Error in fetching olt_ip_output: {e}')
        return {bridge_domain: []}



import pandas as pd
from concurrent.futures import ThreadPoolExecutor
from netmiko import ConnectHandler

# olt_connection = {
#     'device_type': 'cisco_ios',
#     'host': '172.17.224.1',
#     'username': 'praveen.j',
#     'password': 'Nasa@1021',
# }
#
# # Establish SSH connection to the OLT device
# net_connect = ConnectHandler(**olt_connection)
# net_connect.enable()
#
# # Execute the command (show vrf)
# output= connected_olt_ip(net_connect.send_command('show running-config | include hostname'),'172.17.224.1')
# print(output)
# # print(row['ip_address'])
# # print(output)
#
# # Close the connection
# net_connect.disconnect()


#
#
# # Function to process the OLT connection and execute commands
# def process_olt_connection(row):
#     olt_connection = {
#         'device_type': 'cisco_ios',
#         'host': row['ip_address'],
#         'username': 'praveen.j',
#         'password': 'Nasa@1021',
#     }
#
#     try:
#         # Establish SSH connection to the OLT device
#         net_connect = ConnectHandler(**olt_connection)
#         net_connect.enable()
#
#         # Execute the command (show vrf)
#         output = hostname_converter(net_connect.send_command('show running-config | include hostname'), row['ip_address'])
#         # print(row['ip_address'])
#         # print(output)
#         # all_bridge_domains = []
#         # for bd in output:
#         #     if len(bd['Interfaces']) > 1:
#         #         for each_bd in bd['Interfaces'][1:]:
#         #             if each_bd[0] == 'B':
#         #                 all_bridge_domains.append(each_bd)
#         #     elif len(bd['Interfaces']) == 1:
#         #         all_bridge_domains.append(bd['Interfaces'][0])
#         #
#         # for bd in all_bridge_domains:
#         #     port_channel_finder_with_bd(net_connect.send_command(f'sh bridge-domain {bd[2:]}'), row['ip_address'])
#         # # Close the connection
#         # net_connect.disconnect()
#
#     except Exception as e:
#         # Handle exceptions (log or print as needed)
#         # print(f"Error processing OLT {row['ip_address']}: {e}")
#         pass
# # Read the Excel file (limit to first 50 rows as an example)
# static_file_df = pd.read_excel('Routers -All Pkgs.xlsx', engine='openpyxl')
#
# # Define the number of threads for the ThreadPoolExecutor
# MAX_WORKERS = 1000  # You can adjust this based on your system's capability
#
# # Function to run the main process
# def main():
#     with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
#         # Submit tasks to process each OLT device concurrently
#         futures = [executor.submit(process_olt_connection, row) for _, row in static_file_df.iterrows()]
#
#         # Wait for all tasks to complete (optional)
#         for future in futures:
#             future.result()  # This will raise any exceptions encountered in the threads
#
# if __name__ == "__main__":
#     main()
