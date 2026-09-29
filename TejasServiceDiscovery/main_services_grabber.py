import date_time
import pandas as pd
import json
import ont_grabber
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from UpstreamBandwidthObjectMaker import upstream_bandwidth_df
from servicesObjectmaker import ServiceObjectMaker, EndPointsObjectMaker
from downstreamLookup import downstream_profile_lookup
import olt_grabber
import xlsxwriter
import excel_bg
import UpstreamBandwidthObjectMaker
import APIGrabber
import requests
import psycopg2
import logging

services_df = {
    'Vendor': [],
    'Package': [],
    'uuid': [],
    'Service Name': [],
    'Operational state': [],
    'Lifecycle state': [],
    'Administrative state': [],
    'Status': [],
    'Associated vlans': [],
    'Customer': [],
    'GPON Service type': [],
    'GPON type': [],
    'Status Message': [],
    'Total End Points': [],
    'End point': [],
    'Node Connectivity End Point Name': [],
    'Node IP': [],
    'ONT Serial Number': [],
    'Port Label': [],
    'ONT Eth Port Instance': [],
    'Node Admin Status': [],
    'Lifecycle State': [],
    'Vlan Id': [],
    'SVlan Id': [],
    'Ingress Vlan1': [],
    'Class of service': [],
    'Traffic Type': [],
    'Service Type': [],
    'Traffic Origin': [],
    'Upstream Profile Name': [],
    'Downstream Profile Name': [],
    'OLT Hostname': [],
    'OLT District': [],
    'OLT Location': [],
    'OLT Model':[],
    'Num of ONT connected': [],
    'ONT Name': [],
    'ONT Location': [],
    'ONT Model': [],
    'ONT ID': [],
    'Pon Port': [],
    'Downstream PIR': [],
    'Downstream CIR': [],
    'Upstream Max Bandwidth': [],
    'Upstream Assured Bandwidth': [],
    'Upstream Fixed Bandwidth': [],
}

final_services_df = {
    'Vendor': [],
    'Package': [],
    'Unique uuid': [],
    'Service Name': [],
    'Service Type': [],
    'Uplink Port': [],
    'SVLAN': [],
    'Node IP' : [],
    'Total End Points': [],
    'Traffic Origin': [],
    'CVLAN': [],
    'ONT Serial Number': [],
    'ONT Port': [],
    'Traffic Type': [],
    'Upstream Profile Name': [],
    'Downstream Profile Name': [],
    'OLT Hostname': [],
    'OLT Location': [],
    'OLT Model':[],
    'ONT Location': [],
    'ONT Model': [],
    'ONT ID': [],
    'Pon Port': [],
    'Downstream PIR': [],
    'Downstream CIR': [],
    'Upstream Max Bandwidth': [],
    'Upstream Assured Bandwidth': [],
    'Upstream Fixed Bandwidth': [],
}

ont_dataframe = ont_grabber.ont_df_maker()
all_ont_serial_numbers = [row['Serial No'] for index, row in ont_dataframe.iterrows()]
olt_dataframe = olt_grabber.olt_df_maker()
logging.info("=" * 80)
logging.info("OLT Inventory Loaded")

logging.info(f"Rows : {len(olt_dataframe)}")
logging.info(f"Unique OLTs : {olt_dataframe['OLT IP'].nunique()}")
all_olt_ips = [row['OLT IP'] for index, row in olt_dataframe.iterrows()]
upstream_bandwidth_dataframe = UpstreamBandwidthObjectMaker.upstream_bandwidth_df_maker()
all_upstream_names = [row['profile_name'] for index, row in upstream_bandwidth_dataframe.iterrows()]

downstream_lookup = downstream_profile_lookup()

pkgs = ['A', 'B', 'C']

for pkg in pkgs:
    print(pkg)
    service_path = f'Tejaspackage(API_responses)/TejasPkg{pkg}services.json'

    with open(service_path, 'r') as file:
        all_data = json.load(file)
    n = 0

    for data in all_data:
        service_obj = ServiceObjectMaker(data)
        num_of_end_points = service_obj.end_points
        end_point_data = service_obj.end_point_data

        for number in range(0, num_of_end_points):

            services_df['Vendor'].append(service_obj.vendor)
            services_df['Package'].append(f'Package-{pkg}')
            services_df['Service Name'].append(service_obj.connectivity_service)
            services_df['uuid'].append(service_obj.uuid)
            services_df['Operational state'].append(service_obj.operational_state)
            services_df['Lifecycle state'].append(service_obj.lifecycle_state)
            services_df['Administrative state'].append(service_obj.administrative_state)
            services_df['Status'].append(service_obj.status)
            services_df['Associated vlans'].append(service_obj.associated_vlan)
            services_df['Customer'].append(service_obj.customer)
            services_df['GPON Service type'].append(service_obj.gpon_service_type)
            services_df['GPON type'].append(service_obj.gpon_type)
            services_df['Status Message'].append(service_obj.status_msg)
            services_df['Total End Points'].append(service_obj.end_points)
            services_df['End point'].append(number + 1)

            end_point_obj = EndPointsObjectMaker(end_point_data[number], downstream_lookup)

            services_df['Node Connectivity End Point Name'].append(end_point_obj.edge_point_uuid)
            services_df['Node IP'].append(end_point_obj.node_uuid)
            services_df['ONT Serial Number'].append(end_point_obj.serial_number)
            services_df['Port Label'].append(end_point_obj.port_label)
            services_df['ONT Eth Port Instance'].append(end_point_obj.ont_eth_port_instance)
            services_df['Node Admin Status'].append(end_point_obj.node_admin_status)
            services_df['Lifecycle State'].append(end_point_obj.life_cycle_state)
            services_df['Vlan Id'].append(end_point_obj.v_lan_id)
            services_df['SVlan Id'].append(end_point_obj.s_vlan_id)
            services_df['Ingress Vlan1'].append(end_point_obj.ingress_vlan1)
            services_df['Class of service'].append(end_point_obj.cos_name)
            services_df['Traffic Type'].append(end_point_obj.traffic_type)
            services_df['Service Type'].append(end_point_obj.ep_type)
            services_df['Traffic Origin'].append(end_point_obj.traffic_origin)
            services_df['Upstream Profile Name'].append(end_point_obj.upstream_bandwidth_profile_name)
            services_df['Downstream Profile Name'].append(end_point_obj.downstream_bandwidth_profile_name)

            services_df['Downstream PIR'].append(end_point_obj.downstream_pir)
            services_df['Downstream CIR'].append(end_point_obj.downstream_cir)

            olt_ip = end_point_obj.node_uuid
            try:
                olt_index = all_olt_ips.index(olt_ip)
                services_df['OLT Hostname'].append(olt_dataframe.at[olt_index, 'OLT Name'])
                services_df['OLT District'].append(olt_dataframe.at[olt_index, 'District'])
                services_df['OLT Location'].append(olt_dataframe.at[olt_index, 'Location'])
                services_df['OLT Model'].append(olt_dataframe.at[olt_index, 'Product Name'])
                services_df['Num of ONT connected'].append(olt_dataframe.at[olt_index, 'Num of ONT connected'])
            except ValueError:
                services_df['OLT Hostname'].append(None)
                services_df['OLT District'].append(None)
                services_df['OLT Location'].append(None)
                services_df['OLT Model'].append(None)
                services_df['Num of ONT connected'].append(None)

            ont_serial_num = end_point_obj.serial_number
            upstream_profile_name = end_point_obj.upstream_bandwidth_profile_name

            try:
                ont_serial_num_index = all_ont_serial_numbers.index(ont_serial_num)
                upstream_profile_name_index = all_upstream_names.index(upstream_profile_name)
                services_df['ONT Name'].append(ont_dataframe.at[ont_serial_num_index, 'ONT uuid'])
                services_df['ONT Location'].append(ont_dataframe.at[ont_serial_num_index, 'Location'])
                services_df['ONT Model'].append(ont_dataframe.at[ont_serial_num_index, 'Equipment Id'])
                services_df['ONT ID'].append(ont_dataframe.at[ont_serial_num_index, 'Native EMS Name'])
                value = ont_dataframe.at[ont_serial_num_index, 'Pon Port']
                services_df['Pon Port'].append(int(value) if value is not None else None)
                services_df['Upstream Max Bandwidth'].append(upstream_bandwidth_dataframe.at[upstream_profile_name_index, 'max_bandwidth'])
                services_df['Upstream Assured Bandwidth'].append(upstream_bandwidth_dataframe.at[upstream_profile_name_index, 'assured_bandwidth'])
                services_df['Upstream Fixed Bandwidth'].append(upstream_bandwidth_dataframe.at[upstream_profile_name_index, 'fixed_bandwidth'])
            except ValueError:
                services_df['ONT Name'].append(None)
                services_df['ONT Location'].append(None)
                services_df['ONT Model'].append(None)
                services_df['ONT ID'].append(None)
                services_df['Pon Port'].append(None)
                services_df['Upstream Max Bandwidth'].append(None)
                services_df['Upstream Assured Bandwidth'].append(None)
                services_df['Upstream Fixed Bandwidth'].append(None)

            ## final services Data frame .. ...... .....

            final_services_df['Vendor'].append(service_obj.vendor)
            final_services_df['Package'].append(f'Package-{pkg}')
            final_services_df['Unique uuid'].append(service_obj.uuid)
            final_services_df['Service Name'].append(service_obj.connectivity_service)

            if end_point_obj.traffic_origin == 'Server':
                final_services_df['Service Type'].append(end_point_obj.ep_type)
                final_services_df['Uplink Port'].append(end_point_obj.port_label)
                final_services_df['SVLAN'].append(None if end_point_obj.v_lan_id == "NA" and end_point_obj.s_vlan_id == "NA" else end_point_obj.s_vlan_id if end_point_obj.v_lan_id == "NA" else end_point_obj.v_lan_id if end_point_obj.s_vlan_id == "NA" else f"{end_point_obj.v_lan_id}, {end_point_obj.s_vlan_id}")
                final_services_df['Node IP'].append(end_point_obj.node_uuid)
                final_services_df['Total End Points'].append(int(service_obj.end_points))
            else:
                final_services_df['Service Type'].append(None)
                final_services_df['Uplink Port'].append(None)
                final_services_df['SVLAN'].append(None)
                final_services_df['Node IP'].append(None)
                final_services_df['Total End Points'].append(None)

            final_services_df['Traffic Origin'].append(end_point_obj.traffic_origin)
            if end_point_obj.traffic_origin == 'Customer':
                final_services_df['CVLAN'].append(None if end_point_obj.v_lan_id == "NA" and end_point_obj.s_vlan_id == "NA" else end_point_obj.s_vlan_id if end_point_obj.v_lan_id == "NA" else end_point_obj.v_lan_id if end_point_obj.s_vlan_id == "NA" else f"{end_point_obj.v_lan_id}, {end_point_obj.s_vlan_id}")
                final_services_df['ONT Serial Number'].append(end_point_obj.serial_number)
            else:
                final_services_df['CVLAN'].append(None)
                final_services_df['ONT Serial Number'].append(None)
            final_services_df['ONT Port'].append(end_point_obj.port_label)
            final_services_df['Traffic Type'].append(end_point_obj.traffic_type)
            final_services_df['Upstream Profile Name'].append(end_point_obj.upstream_bandwidth_profile_name)
            final_services_df['Downstream Profile Name'].append(end_point_obj.downstream_bandwidth_profile_name)

            final_services_df['Downstream PIR'].append(end_point_obj.downstream_pir)
            final_services_df['Downstream CIR'].append(end_point_obj.downstream_cir)

            try:
                olt_index = all_olt_ips.index(olt_ip)
                final_services_df['OLT Hostname'].append(olt_dataframe.at[olt_index, 'OLT Name'])
                final_services_df['OLT Location'].append(olt_dataframe.at[olt_index, 'Location'])
                final_services_df['OLT Model'].append(olt_dataframe.at[olt_index, 'Product Name'])
            except ValueError:
                final_services_df['OLT Hostname'].append(None)
                final_services_df['OLT Location'].append(None)
                final_services_df['OLT Model'].append(None)

            try:
                ont_serial_num_index = all_ont_serial_numbers.index(ont_serial_num)
                upstream_profile_name_index = all_upstream_names.index(upstream_profile_name)
                final_services_df['ONT Location'].append(ont_dataframe.at[ont_serial_num_index, 'Location'])
                final_services_df['ONT Model'].append(ont_dataframe.at[ont_serial_num_index, 'Equipment Id'])
                final_services_df['ONT ID'].append(ont_dataframe.at[ont_serial_num_index, 'Native EMS Name'])
                final_services_df['Pon Port'].append(ont_dataframe.at[ont_serial_num_index, 'Pon Port'])
                final_services_df['Upstream Max Bandwidth'].append(upstream_bandwidth_dataframe.at[upstream_profile_name_index, 'max_bandwidth'])
                final_services_df['Upstream Assured Bandwidth'].append(upstream_bandwidth_dataframe.at[upstream_profile_name_index, 'assured_bandwidth'])
                final_services_df['Upstream Fixed Bandwidth'].append(upstream_bandwidth_dataframe.at[upstream_profile_name_index, 'fixed_bandwidth'])
            except ValueError:
                final_services_df['ONT Location'].append(None)
                final_services_df['ONT Model'].append(None)
                final_services_df['ONT ID'].append(None)
                final_services_df['Pon Port'].append(None)
                final_services_df['Upstream Max Bandwidth'].append(None)
                final_services_df['Upstream Assured Bandwidth'].append(None)
                final_services_df['Upstream Fixed Bandwidth'].append(None)


# service_df = pd.DataFrame(services_df)
finals_services_df = pd.DataFrame(final_services_df)

# Convert 'Total End Points' column to string type to avoid FutureWarning
finals_services_df['Total End Points'] = finals_services_df['Total End Points'].astype(str)

index_list = []
present_uuid = finals_services_df['Unique uuid'][0]
service_type = ''
uplink_port = ''
svlan = ''
node_ip =''
end_points = ''

for index, row in finals_services_df.iterrows():
    if row['Unique uuid'] == present_uuid:
        index_list.append(index)
        if row['Traffic Origin'] == 'Server':
            if service_type == '':
                service_type += row['Service Type']
                uplink_port += row['Uplink Port']
                svlan += str(row['SVLAN'])
                node_ip += row['Node IP']
                end_points += str(int(float(row['Total End Points'])))
            else:
                if not service_type == row['Service Type']:
                    service_type += f", {row['Service Type']:}"
                if not uplink_port == row['Uplink Port']:
                    uplink_port += f", {row['Uplink Port']}"
                if not svlan == str(row['SVLAN']):
                    svlan += f", {str(row['SVLAN'])}"
                if not node_ip == row['Node IP']:
                    node_ip += f", {row['Node IP']}"
                if not end_points == f"{str(int(float(row['Total End Points'])))}":
                    end_points += f", {str(int(float(row['Total End Points'])))}"
    else:
        present_uuid = row['Unique uuid']
        for i in index_list:
            finals_services_df.at[i, 'Service Type'] = service_type
            finals_services_df.at[i, 'Uplink Port'] = uplink_port
            finals_services_df.at[i, 'SVLAN'] = svlan
            finals_services_df.at[i, 'Node IP'] = node_ip
            finals_services_df.at[i, 'Total End Points'] = end_points
        index_list = []
        service_type = ''
        uplink_port = ''
        svlan = ''
        node_ip = ''
        end_points = ''

        index_list.append(index)
        if row['Traffic Origin'] == 'Server':
            if service_type == '':
                service_type += row['Service Type']
                uplink_port += row['Uplink Port']
                svlan += str(row['SVLAN'])
                node_ip += row['Node IP']
                end_points += str(int(float(row['Total End Points'])))
            else:
                if not service_type == row['Service Type']:
                    service_type += f", {row['Service Type']:}"
                if not uplink_port == row['Uplink Port']:
                    uplink_port += f", {row['Uplink Port']}"
                if not svlan == str(row['SVLAN']):
                    svlan += f", {str(row['SVLAN'])}"
                if not node_ip == row['Node IP']:
                    node_ip += f", {row['Node IP']}"
                if not end_points == f"{str(int(float(row['Total End Points'])))}":
                    end_points += f", {str(int(float(row['Total End Points'])))}"

for i in index_list:
    finals_services_df.at[i, 'Service Type'] = service_type
    finals_services_df.at[i, 'Uplink Port'] = uplink_port
    finals_services_df.at[i, 'SVLAN'] = svlan
    finals_services_df.at[i, 'Node IP'] = node_ip
    finals_services_df.at[i, 'Total End Points'] = end_points

finals_services_df = pd.DataFrame(finals_services_df)

print(finals_services_df.columns)

for index, row in finals_services_df.iterrows():
    if row['Traffic Origin'] == 'Server':
        finals_services_df = finals_services_df.drop(index=index)

finals_services_df.drop(columns=['Total End Points', 'Traffic Origin', 'Unique uuid'], inplace=True)

# def combine_values(series):
#     return ', '.join(map(str, series.unique())) if len(series.unique()) > 1 else str(series.iloc[0])
#
# # Group by both 'key1' and 'key2'
# finals_services_df = finals_services_df.groupby(['OLT Hostname', 'ONT Port', 'Package'], as_index=False).agg(combine_values)

# CHANGED: rename to match push_data.py's expected no-space column names,
# then include them in the final selection (previously they were computed
# nowhere AND dropped here even if they had been).
finals_services_df.rename(columns={'Downstream PIR': 'DownstreamPIR', 'Downstream CIR': 'DownstreamCIR'}, inplace=True)

finals_services_df = finals_services_df[['Vendor', 'Package', 'OLT Hostname', 'OLT Location', 'ONT Port', 'Service Name', 'Service Type', 'Uplink Port', 'SVLAN', 'Traffic Type',
                           'Node IP', 'CVLAN', 'Upstream Profile Name', 'Downstream Profile Name', 'ONT ID', 'ONT Serial Number', 'ONT Location',
                           'ONT Model', 'Pon Port', 'OLT Model', 'DownstreamPIR', 'DownstreamCIR',
                           'Upstream Max Bandwidth', 'Upstream Assured Bandwidth', 'Upstream Fixed Bandwidth']]


date = date_time.current_date()
path = f"Reports/{date}ServiceDiscovery.xlsx"
with pd.ExcelWriter(path, engine='xlsxwriter') as writer:
    finals_services_df.to_excel(writer, sheet_name='ServiceDiscovery', index=False)
    ont_dataframe.to_excel(writer, sheet_name='ONTInventory', index=False)
    olt_dataframe.to_excel(writer, sheet_name='OLTInventory', index=False)

today_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

finals_services_df['First Found time'] = today_date
finals_services_df['Last Update time'] = today_date