import pandas as pd
import json
import math
from ONTObjectmaker import ONTObjectMaker

ont_df = {
    'Vendor': [],
    'Pacakge': [],
    'device': [],
    'Location': [],
    'ONT uuid': [],
    'Equipment Holder': [],
    'Slot': [],
    'ONT ID': [],
    'Pon Port' : [],
    'Native EMS Name': [],
    'Equipment Id': [],
    'Serial No' : [],
    'OLT IP' : [],
    'Admin Status' : [],
    'Physical Status' : [],
    'PM Status': [],
    'Is Duplicate' : [],
    'Mode': [],
    'Distance from OLT': [],
    'Total Gem Port Ids': [],
    'Vendor Id': [],
    'Last Unavailable Time': [],
    'Last Available Time' : [],
    'Node Create Time' : [],
    'Node Modify Time': [],
    'Software Version': [],
    'Active Software Version': [],
    'MAC Address': [],
    'Num Cards': [],
    'Associated max Bandwidth': [],
    'Associated Assured Bandwidth': [],
    'Associated Fixed Bandwidth': [],
    'Associated Outer vlan': [],
    'Associated Translated vlan': [],
    'Total Node Edge Points': [],
}

def ont_df_maker():
    pkgs = ['A', 'B', 'C']
    for pkg in pkgs:
        file_name =f'Tejaspackage(API_responses)/TejasPkg{pkg}ont_count.json'
        with open(file_name, 'r') as file:
            list_length = len(json.load(file))
        ont_count = int(math.ceil(list_length / 500))

        for i in range(ont_count):
            with open(fr'Tejaspackage(API_responses)/TejasPkg{pkg}ont{i}.json', 'r') as file:
                all_data = json.load(file)
            for data in all_data:
                ont_object = ONTObjectMaker(data, pkg)
                ont_df['Vendor'].append(ont_object.vendor)
                ont_df['Pacakge'].append(ont_object.pacakge)
                ont_df['device'].append(ont_object.device)
                ont_df['Location'].append(ont_object.location)
                ont_df['ONT uuid'].append(ont_object.ont_uuid)
                ont_df['Equipment Holder'].append(ont_object.EquipmentHolder)
                ont_df['Slot'].append(ont_object.slot)
                ont_df['ONT ID'].append(ont_object.shelf)
                ont_df['Pon Port'].append(ont_object.pon_port)
                ont_df['Native EMS Name'].append(ont_object.nativeEMSName)
                ont_df['Equipment Id'].append(ont_object.EquipmentId)
                ont_df['Serial No'].append(ont_object.SerialNo)
                ont_df['OLT IP'].append(ont_object.ManagedElement)
                ont_df['Admin Status'].append(ont_object.AdminState)
                ont_df['Physical Status'].append(ont_object.PhysicalStatus)
                ont_df['PM Status'].append(ont_object.PMStatus)
                ont_df['Is Duplicate'].append(ont_object.IsDuplicate)
                ont_df['Mode'].append(ont_object.Mode)
                ont_df['Distance from OLT'].append(ont_object.Distance)
                ont_df['Total Gem Port Ids'].append(ont_object.TotalGemPortIds)
                ont_df['Vendor Id'].append(ont_object.VendorId)
                ont_df['Last Unavailable Time'].append(ont_object.LastONTGUnavailableTime)
                ont_df['Last Available Time'].append(ont_object.LastONTGAvailableTime)
                ont_df['Node Create Time'].append(ont_object.NodeCreateTime)
                ont_df['Node Modify Time'].append(ont_object.NodeModifyTime)
                ont_df['Software Version'].append(ont_object.SwVersion)
                ont_df['Active Software Version'].append(ont_object.ActiveSwVersion)
                ont_df['MAC Address'].append(ont_object.MACAddress)
                ont_df['Num Cards'].append(ont_object.NumCards)
                ont_df['Associated max Bandwidth'].append(ont_object.associated_max_bandwidth)
                ont_df['Associated Assured Bandwidth'].append(ont_object.associated_assured_bandwidth)
                ont_df['Associated Fixed Bandwidth'].append(ont_object.associated_fixed_bandwidth)
                ont_df['Associated Outer vlan'].append(ont_object.associated_outer_vlan)
                ont_df['Associated Translated vlan'].append(ont_object.associated_translated_vlan)
                ont_df['Total Node Edge Points'].append(ont_object.total_node_edge_point)

    return pd.DataFrame(ont_df)







