from CiscoInfoGrabber import CiscoInfoGrabber
import pandas as pd
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

RouterInfo = {
    'Static_EMS_Name': [],
    'Static_Router_IP': [],
    'Static_Hostname': [],
    'Hostname': [],
    'Router_Model': [],
    'Router_Serial_No': [],
    'Status': [],
    'LastUpdateTime': [],
}

VrfInfo ={
    'Hostname': [],
    'Service_Name': [],
    'Default_RD': [],
    'Interfaces': [],
    'L3VPN_Type': [],
    'L3VPN_Import_RT': [],
    'L3VPN_Export_RT': [],
}

BridgeDomainInfo = {
    'Hostname': [],
    'Bridge_Domain': [],
    'BDI_Status': [],
    'Line_Protocol_Status': [],
    'Description': [],
    'Connected_OLT_IP': [],
    'Input_Traffic': [],
    'Output_Traffic': [],
}

PortChannelInfo = {
    'Hostname': [],
    'Description': [],
    'Port_Channel': [],
    'Port_Channel_Status': [],
    'Line_Protocol_Status': [],
    'VLAN': [],
    'VLAN_Description': [],
    'Encapsulation': [],
    'Bridge_Domain': [],
    'Service_Policy_Input': [],
    'Physical_Interface_(BD)': [],
}

CDPNeighInfo = {
    'Hostname': [],
    'Device_ID': [],
    'Local_Interface_Port' : [],
    'Model': [],
    'End_Point_Interface_Port': [],
}

ErrorRouters = {
    'Router_IP': [],
    'EMS_Name': [],
    'Error': [],
}

# static_file_df = pd.read_excel('test_routers.xlsx', engine='openpyxl')

static_file_df = pd.read_excel('Routers -All Pkgs.xlsx', engine='openpyxl')


def process_router(row):
    ip = row['ip_address']
    ems = row['EMS Name']
    name = row['device_name']
    try:
        grabber = CiscoInfoGrabber(ip)
        grabber = grabber.get_router_info()
        if len(grabber) > 3:

            router_data = {
                'Static_EMS_Name': ems,
                'Static_Router_IP': ip,
                'Static_Hostname': name,
                'Router_Model': grabber['Chassis Information'].get('Router Model', None),
                'Router_Serial_No': grabber['Chassis Information'].get('Router Serial No', None),
                'Hostname': grabber.get('Hostname', None),
                'Status': 'UP',
                'LastUpdateTime': datetime.now().strftime("%d/%m/%y %H:%M:%S"),
            }

            vrf_data = []
            for index, service in enumerate(grabber.get('Vrf Information', [])):
                vrf_data.append({
                    'Hostname': grabber.get('Hostname', None),
                    'Service_Name': service['service_name'],
                    'Default_RD': service['Default RD'],
                    'Interfaces': ', '.join(service['Interfaces']),
                    'L3VPN_Type': grabber['L3VPN Information'][index][service['service_name']].get('L3VPN Type', None),
                    'L3VPN_Import_RT': ', '.join(
                        grabber['L3VPN Information'][index][service['service_name']].get('L3VPN Import RT', None)),
                    'L3VPN_Export_RT': ', '.join(
                        grabber['L3VPN Information'][index][service['service_name']].get('L3VPN Export RT', None)),
                })

            bridge_domain_data = []
            for bd_key, bd in grabber.get('Bridge Domain Status', {}).items():
                con_olt_ip = ', '.join(grabber['Connected OLT IP'].get(bd_key, [])) if grabber['Connected OLT IP'].get(bd_key, None) else None
                bridge_domain_data.append({
                    'Hostname': grabber.get('Hostname', None),
                    'Bridge_Domain': bd_key,
                    'BDI_Status': bd.get('BDI status', None),
                    'Line_Protocol_Status': bd.get('Line-protocol Status', None),
                    'Description': bd.get('Description', None),
                    'Connected_OLT_IP': con_olt_ip,
                    'Input_Traffic': bd.get('Input Traffic status on BDI', None),
                    'Output_Traffic': bd.get('Output Traffic status on BDI', None),
                })

            port_channel_data = []
            for index, port_channel_name in enumerate(grabber.get('Total Port Channels', [])):
                port_channel_info = grabber['Port Channel Information'][index][port_channel_name]
                for service in port_channel_info.get('Service Instances', []):
                    port_channel_data.append({
                        'Hostname': grabber.get('Hostname', None),
                        'Port_Channel': port_channel_name,
                        'Description': port_channel_info.get('Description', None),
                        'Bridge_Domain': service.get('Bridge Domain', None),
                        'Port_Channel_Status': grabber['Port Channel Status'][index][port_channel_name].get(
                            'Port-channel Status', None),
                        'Line_Protocol_Status': grabber['Port Channel Status'][index][port_channel_name].get(
                            'Line-protocol Status', None),
                        'Physical_Interface_(BD)': ', '.join(
                            grabber['Port Channel Status'][index][port_channel_name].get(
                                'Physical interface status bound to BD', None)),
                        'VLAN': service.get('VLAN', None),
                        'VLAN_Description': service.get('description', None),
                        'Encapsulation': service.get('encapsulation', None),
                        'Service_Policy_Input': service.get('Service Policy Input', None),
                    })

            cdp_data = []
            for cdp_host in grabber['CDP Neighbors'].get('CDPs Information', []):
                cdp_data.append({
                    'Hostname': grabber.get('Hostname', None),
                    'Device_ID': cdp_host.get('Device ID', None),
                    'Local_Interface_Port': cdp_host.get('Local Interface Port', None),
                    'Model': cdp_host.get('Model', None),
                    'End_Point_Interface_Port': cdp_host.get('End Point Interface Port', None),
                })

            return router_data, vrf_data, bridge_domain_data, port_channel_data, cdp_data, None
        else:
            # If the router info is incomplete or invalid, return None for router_data and empty lists for the rest
            return {
                'Static_EMS_Name': ems,
                'Static_Router_IP': ip,
                'Static_Hostname': name,
                'Router_Model': None,
                'Router_Serial_No': None,
                'Hostname': None,
                'Status': 'DOWN',
                'LastUpdateTime': None,
            }, [], [], [], [], None

    except Exception as e:
        print(e)
        error_data = {
            'Router_IP': ip,
            'EMS_Name': ems,
            'Error': str(e),
        }
        return None, [], [], [], [], error_data

# Create a ThreadPoolExecutor with 10 workers
with ThreadPoolExecutor(max_workers=300) as executor:
    futures = {executor.submit(process_router, row): row for _, row in static_file_df.iterrows()}

    for index, future in enumerate(as_completed(futures)):
        router_data, vrf_data, bridge_domain_data, port_channel_data, cdp_data, error_data = future.result()
        # print(f"Completed processing {index} routers...")

        if router_data:
            RouterInfo['Static_EMS_Name'].append(router_data['Static_EMS_Name'])
            RouterInfo['Static_Router_IP'].append(router_data['Static_Router_IP'])
            RouterInfo['Static_Hostname'].append(router_data['Static_Hostname'])
            RouterInfo['Router_Model'].append(router_data['Router_Model'])
            RouterInfo['Router_Serial_No'].append(router_data['Router_Serial_No'])
            RouterInfo['Hostname'].append(router_data['Hostname'])
            RouterInfo['Status'].append(router_data['Status'])
            RouterInfo['LastUpdateTime'].append(router_data['LastUpdateTime'])

        for vrf in vrf_data:
            VrfInfo['Hostname'].append(vrf['Hostname'])
            VrfInfo['Service_Name'].append(vrf['Service_Name'])
            VrfInfo['Default_RD'].append(vrf['Default_RD'])
            VrfInfo['Interfaces'].append(vrf['Interfaces'])
            VrfInfo['L3VPN_Type'].append(vrf['L3VPN_Type'])
            VrfInfo['L3VPN_Import_RT'].append(vrf['L3VPN_Import_RT'])
            VrfInfo['L3VPN_Export_RT'].append(vrf['L3VPN_Export_RT'])

        for bd in bridge_domain_data:
            BridgeDomainInfo['Hostname'].append(bd['Hostname'])
            BridgeDomainInfo['Bridge_Domain'].append(bd['Bridge_Domain'])
            BridgeDomainInfo['BDI_Status'].append(bd['BDI_Status'])
            BridgeDomainInfo['Line_Protocol_Status'].append(bd['Line_Protocol_Status'])
            BridgeDomainInfo['Description'].append(bd['Description'])
            BridgeDomainInfo['Connected_OLT_IP'].append(bd['Connected_OLT_IP'])
            BridgeDomainInfo['Input_Traffic'].append(bd['Input_Traffic'])
            BridgeDomainInfo['Output_Traffic'].append(bd['Output_Traffic'])

        for pc in port_channel_data:
            PortChannelInfo['Hostname'].append(pc['Hostname'])
            PortChannelInfo['Port_Channel'].append(pc['Port_Channel'])
            PortChannelInfo['Description'].append(pc['Description'])
            PortChannelInfo['Bridge_Domain'].append(pc['Bridge_Domain'])
            PortChannelInfo['Port_Channel_Status'].append(pc['Port_Channel_Status'])
            PortChannelInfo['Line_Protocol_Status'].append(pc['Line_Protocol_Status'])
            PortChannelInfo['Physical_Interface_(BD)'].append(pc['Physical_Interface_(BD)'])
            PortChannelInfo['VLAN'].append(pc['VLAN'])
            PortChannelInfo['VLAN_Description'].append(pc['VLAN_Description'])
            PortChannelInfo['Encapsulation'].append(pc['Encapsulation'])
            PortChannelInfo['Service_Policy_Input'].append(pc['Service_Policy_Input'])

        for cdp in cdp_data:
            CDPNeighInfo['Hostname'].append(cdp['Hostname'])
            CDPNeighInfo['Device_ID'].append(cdp['Device_ID'])
            CDPNeighInfo['Local_Interface_Port'].append(cdp['Local_Interface_Port'])
            CDPNeighInfo['Model'].append(cdp['Model'])
            CDPNeighInfo['End_Point_Interface_Port'].append(cdp['End_Point_Interface_Port'])

        # If there's an error, log the router IP with error
        if error_data:
            ErrorRouters['Router_IP'].append(error_data['Router_IP'])
            ErrorRouters['EMS_Name'].append(error_data['EMS_Name'])
            ErrorRouters['Error'].append(error_data['Error'])


pd.DataFrame(RouterInfo).to_csv('E:/Discovery_Data/IPMPLS/RouterInfo.csv', index=False)
pd.DataFrame(VrfInfo).to_csv('E:/Discovery_Data/IPMPLS/VRFInfo.csv', index=False)
pd.DataFrame(BridgeDomainInfo).to_csv('E:/Discovery_Data/IPMPLS/BridgeDomainInfo.csv', index=False)
pd.DataFrame(PortChannelInfo).to_csv('E:/Discovery_Data/IPMPLS/PortChannelInfo.csv', index=False)
pd.DataFrame(CDPNeighInfo).to_csv('E:/Discovery_Data/IPMPLS/CDPNeighInfo.csv', index=False)
pd.DataFrame(ErrorRouters).to_csv('E:/Discovery_Data/IPMPLS/ErrorRouters.csv', index=False)

# # Create a Pandas Excel writer using XlsxWriter as the engine
# with pd.ExcelWriter('IPMPLSDiscovery_test.xlsx', engine='xlsxwriter') as writer:
#     # Write each dataframe to a different worksheet
#     pd.DataFrame(RouterInfo).to_excel(writer, sheet_name='RouterInfo', index=False)
#     pd.DataFrame(VrfInfo).to_excel(writer, sheet_name='VRFInfo', index=False)
#     pd.DataFrame(BridgeDomainInfo).to_excel(writer, sheet_name='BridgeDomainInfo', index=False)
#     pd.DataFrame(PortChannelInfo).to_excel(writer, sheet_name='PortChannelInfo', index=False)
#     pd.DataFrame(CDPNeighInfo).to_excel(writer, sheet_name='CDPNeighInfo', index=False)
#
#     # Write the Error routers to a separate sheet
#     pd.DataFrame(ErrorRouters).to_excel(writer, sheet_name='ErrorRouters', index=False)