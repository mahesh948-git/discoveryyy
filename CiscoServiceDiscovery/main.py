from CiscoInfoGrabber import CiscoInfoGrabber
# import data
import pandas as pd
from datetime import datetime

RouterInfo = {
    'EMS_Name': [],
    'Router_IP': [],
    'Hostname': [],
    'Router_Model': [],
    'Router_Serial_No': [],
    'Connected_OLT_IPs': [],
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
    'Input_Traffic': [],
    'Output_Traffic': [],
}

PortChannelInfo = {
    'Hostname': [],
    'Description': [],
    'Port_Channel': [],
    'Port_Channel_Status': [],
    'Line_Protocol_Status': [],
    'Physical_Interface_(BD)': [],
    'VLAN': [],
    'VLAN_Description': [],
    'Encapsulation': [],
    'Bridge_Domain': [],
    'Service_Policy_Input': [],
}

CDPNeighInfo = {
    'Hostname': [],
    'Device_ID': [],
    'Local_Interface_Port' : [],
    'Model': [],
    'End_Point_Interface_Port': [],
}

static_file_df = pd.read_excel('test_routers.xlsx', engine='openpyxl')

for i, row in static_file_df.iterrows():
    ip = row['ip_address']
    ems = row['EMS Name']

    grabber = CiscoInfoGrabber(ip)
    grabber = grabber.get_router_info()
    try:
        if len(grabber) > 3:
            RouterInfo['EMS_Name'].append(ems)
            RouterInfo['Router_IP'].append(ip)
            RouterInfo['Router_Model'].append(grabber['Chassis Information'].get('Router Model', None))
            RouterInfo['Router_Serial_No'].append(grabber['Chassis Information'].get('Router Serial No', None))
            RouterInfo['Hostname'].append(grabber.get('Hostname', None))
            RouterInfo['Connected_OLT_IPs'].append(', '.join(grabber.get('Connected OLT IP', None)))
            now = datetime.now()
            formatted_now = now.strftime("%d/%m/%y %H:%M:%S")
            RouterInfo['LastUpdateTime'].append(formatted_now)

            for index, service in enumerate(grabber.get('Vrf Information', [])):
                service_name = service['service_name']
                VrfInfo['Hostname'].append(grabber.get('Hostname', None))
                VrfInfo['Service_Name'].append(service['service_name'])
                VrfInfo['Default_RD'].append(service['Default RD'])
                VrfInfo['Interfaces'].append(', '.join(service['Interfaces']))
                VrfInfo['L3VPN_Type'].append(grabber['L3VPN Information'][index][service_name].get('L3VPN Type', None))
                VrfInfo['L3VPN_Import_RT'].append(', '.join(grabber['L3VPN Information'][index][service_name].get('L3VPN Import RT', None)))
                VrfInfo['L3VPN_Export_RT'].append(', '.join(grabber['L3VPN Information'][index][service_name].get('L3VPN Export RT', None)))

            for bd_key, bd in grabber.get('Bridge Domain Status', {}).items():
                BridgeDomainInfo['Hostname'].append(grabber.get('Hostname', None)),
                BridgeDomainInfo['Bridge_Domain'].append(bd_key),
                BridgeDomainInfo['BDI_Status'].append(bd.get('BDI status', None)),
                BridgeDomainInfo['Line_Protocol_Status'].append(bd.get('Line-protocol Status', None)),
                BridgeDomainInfo['Description'].append(bd.get('Description', None)),
                BridgeDomainInfo['Input_Traffic'].append(bd.get('Input Traffic status on BDI', None)),
                BridgeDomainInfo['Output_Traffic'].append(bd.get('Output Traffic status on BDI', None)),

            for index, port_channel_name in enumerate(grabber.get('Total Port Channels', [])):
                port_channel_info = grabber['Port Channel Information'][index][port_channel_name]
                for service in port_channel_info.get('Service Instances', []):
                    PortChannelInfo['Hostname'].append(grabber.get('Hostname', None))
                    PortChannelInfo['Port_Channel'].append(port_channel_name)
                    PortChannelInfo['Description'].append(port_channel_info.get('Description', None))
                    PortChannelInfo['Bridge_Domain'].append(service.get('Bridge Domain', None))
                    PortChannelInfo['Port_Channel_Status'].append(grabber['Port Channel Status'][index][port_channel_name].get('Port-channel Status', None))
                    PortChannelInfo['Line_Protocol_Status'].append(grabber['Port Channel Status'][index][port_channel_name].get('Line-protocol Status', None))
                    PortChannelInfo['Physical_Interface_(BD)'].append(', '.join(grabber['Port Channel Status'][index][port_channel_name].get('Physical interface status bound to BD', None)))
                    PortChannelInfo['VLAN'].append(service.get('VLAN', None))
                    PortChannelInfo['VLAN_Description'].append(service.get('description', None))
                    PortChannelInfo['Encapsulation'].append(service.get('encapsulation', None))
                    PortChannelInfo['Service_Policy_Input'].append(service.get('Service Policy Input', None))

            for cdp_host in grabber['CDP Neighbors'].get('CDPs Information', []):
                CDPNeighInfo['Hostname'].append(grabber.get('Hostname', None))
                CDPNeighInfo['Device_ID'].append(cdp_host.get('Device ID', None)),
                CDPNeighInfo['Local_Interface_Port'].append(cdp_host.get('Local Interface Port', None))
                CDPNeighInfo['Model'].append(cdp_host.get('Model', None))
                CDPNeighInfo['End_Point_Interface_Port'].append(cdp_host.get('End Point Interface Port', None))
        else:
            RouterInfo['EMS_Name'].append(ems)
            RouterInfo['Router_IP'].append(ip)
            RouterInfo['Router_Model'].append(None)
            RouterInfo['Router_Serial_No'].append(None)
            RouterInfo['Hostname'].append(None)
            RouterInfo['Connected_OLT_IPs'].append(None)
            RouterInfo['LastUpdateTime'].append(None)
    except Exception as e:
        print(e)
        continue

router_df = pd.DataFrame(RouterInfo)
vrf_df = pd.DataFrame(VrfInfo)
bd_df = pd.DataFrame(BridgeDomainInfo)
pc_df = pd.DataFrame(PortChannelInfo)
cdp_df = pd.DataFrame(CDPNeighInfo)

# Create a Pandas Excel writer using XlsxWriter as the engine
with pd.ExcelWriter('IPMPLSDiscovery_test_11_44.xlsx', engine='xlsxwriter') as writer:
    # Write each dataframe to a different worksheet
    router_df.to_excel(writer, sheet_name='RouterInfo', index=False)
    vrf_df.to_excel(writer, sheet_name='VRFInfo', index=False)
    bd_df.to_excel(writer, sheet_name='BridgeDomainInfo', index=False)
    pc_df.to_excel(writer, sheet_name='PortChannelInfo', index=False)
    cdp_df.to_excel(writer, sheet_name='CDPNeighInfo', index=False)

