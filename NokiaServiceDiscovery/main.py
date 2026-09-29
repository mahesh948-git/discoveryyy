from ctypes.wintypes import PRECT
import pandas as pd
import os
import openpyxl
import bg_excel
import nokia_file_processing
from typing import Optional, Dict
from issue_clean import clean_files

final_services_df = {
    'Vendor': [], 'Package': [], 'ONT Port': [], 'Traffic Type': [], 'CVLAN': [],
    'SVLAN': [], 'OLT Hostname': [], 'Service Type': [], 'ONT ID': [], 'Service Name': [],
    'Node IP': [], 'OLT Location': [], 'OLT Model': [], 'Uplink Port': [], 'ONT Serial Number': [],
    'ONT Model': [], 'ONT Location': [], 'Pon Port': [], 'Upstream Profile Name': [],
    'Downstream Profile Name': [], 'Upstream Max Bandwidth': [], 'Upstream Assured Bandwidth': [],
    'Upstream Fixed Bandwidth': [], 'DownstreamPIR': [], 'DownstreamCIR': []
}

PKGS = ['A', 'B', 'C']

n = 0

for pkg in PKGS:
    print(pkg)
    file_path = 'E:/NOKIA_AMS_GPON_Daily_Discovery'
    full_file_path = f"{file_path}/NOKIA_PKG_{pkg}"
    print(full_file_path)
    all_files = nokia_file_processing.file_processing(full_file_path)
    print(all_files)
    if all_files and len(all_files) == 9 and any(all_files.values()):
        print(all_files)
        services_info_path = f"{full_file_path}/{all_files['PORT_S_C_VLAN']}"
        print(services_info_path)
        output_path = os.path.splitext(services_info_path)[0] + "_issuecleared.csv"

        print("Output file:", output_path)

        try:
            if os.path.exists(output_path):
                os.remove(output_path)
                print("Deleted existing output.")
        except Exception as e:
            print("Delete failed:", e)

        services_info_path = clean_files(services_info_path)
        services_info_path = clean_files(services_info_path)
        service_name_path = f"{full_file_path}/{all_files['OLT_VLAN_LIST']}"
        olt_info_path = f"{full_file_path}/{all_files['OSS_NE_DATA']}"
        ont_info_path = f"{full_file_path}/{all_files['OSS_ONT_DATA']}"
        uplink_port_path = f"{full_file_path}/{all_files['Chassis_Uplink_Service']}"
        ont_download_bw_path = f"{full_file_path}/{all_files['ONT_Download']}"
        ont_upload_bw_path = f"{full_file_path}/{all_files['ONT_Upload']}"
        olt_download_bw_path = f"{full_file_path}/{all_files['OLT_Download']}"
        olt_upload_bw_path = f"{full_file_path}/{all_files['OLT_Upload']}"

        services_info_df = pd.read_csv(services_info_path, encoding="utf-8", index_col=False)
        service_name_df = pd.read_csv(service_name_path, encoding="utf-8", index_col=False)
        olt_info_df = pd.read_csv(olt_info_path, encoding="utf-8", index_col=False)
        ont_info_df = pd.read_csv(ont_info_path, encoding="utf-8", index_col=False)
        uplink_port_df = pd.read_csv(uplink_port_path, encoding="utf-8", index_col=False)
        ont_download_bw_df = pd.read_csv(ont_download_bw_path, encoding="utf-8", index_col=False)
        ont_upload_bw_df = pd.read_csv(ont_upload_bw_path, encoding="utf-8", index_col=False)
        olt_download_bw_df = pd.read_csv(olt_download_bw_path, encoding="utf-8", index_col=False)
        olt_upload_bw_df = pd.read_csv(olt_upload_bw_path, encoding="utf-8", index_col=False)

        # Strip whitespace from column headers

        # df.columns = df.columns.str.strip()

        pd.set_option('display.max_rows', None)
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', None)

        # Apply reset_index() to the dataframes outside the loop
        service_name_df.columns = service_name_df.columns.str.strip()
        olt_info_df.columns = olt_info_df.columns.str.strip()
        uplink_port_df.columns = uplink_port_df.columns.str.strip()
        ont_info_df.columns = ont_info_df.columns.str.strip()
        ont_upload_bw_df.columns = ont_upload_bw_df.columns.str.strip()
        ont_download_bw_df.columns = ont_download_bw_df.columns.str.strip()
        olt_upload_bw_df.columns = olt_upload_bw_df.columns.str.strip()
        services_info_df.columns = services_info_df.columns.str.strip()

        print('service name ..')
        print(service_name_df.columns)
        print(service_name_df.head())
        print('olt info ..')
        print(olt_info_df.columns)
        print(olt_info_df.head())
        print('uplink port ..')
        print(uplink_port_df.columns)
        print(uplink_port_df.head())
        print('ont info ..')
        print(ont_info_df.columns)
        print(ont_info_df.head())
        print('ont upload ..')
        print(ont_upload_bw_df.columns)
        print(ont_upload_bw_df.head())
        print('ont download  ..')
        print(ont_download_bw_df.columns)
        print(ont_download_bw_df.head())
        print('olt upload ..')
        print(olt_upload_bw_df.columns)
        print(olt_upload_bw_df.head())
        print('service info ')
        print(services_info_df.columns)
        print(services_info_df.head())

        for index, row in services_info_df.iterrows():
            print(n)
            n = n + 1
            ont_port_value = str(row['@EFM Bridge Port/Virtual UNI/...'])
            print(ont_port_value)
            if ont_port_value[:4] == 'UNI:':
                final_services_df['Vendor'].append('NOKIA')
                final_services_df['Package'].append(f'Package-{pkg}')
                final_services_df['ONT Port'].append(ont_port_value[4:])
                final_services_df['Traffic Type'].append(str(row['Send Frames Back To Subscriber AS']))
                final_services_df['CVLAN'].append(int(row['Port C-VLAN ID']))

                # S_VLAN and Service Type
                s_vlan_final = None
                s_vlan_initial = row['L2 Forwarder VLAN'].split(' ')
                if s_vlan_initial[0] == '-None-':
                    s_vlan_final = int(row['Port C-VLAN ID'])
                    final_services_df['SVLAN'].append(int(row['Port C-VLAN ID']))
                    final_services_df['Service Type'].append('EP_Dot1q')
                else:
                    s_vlan_final = s_vlan_initial[0]
                    final_services_df['SVLAN'].append(s_vlan_initial[0])
                    if s_vlan_initial[0][0] == 'S':
                        final_services_df['Service Type'].append('EP_Dot1ad_with_Dot1q')
                    else:
                        final_services_df['Service Type'].append('EP_Dot1q')

                final_services_df['OLT Hostname'].append(row['NE'])
                ont_id = '.'.join(ont_port_value.split('.')[:-2])[4:]
                final_services_df['ONT ID'].append(ont_id)

                # service Name
                object_name_to_search_service = None
                if isinstance(s_vlan_final, int):
                    object_name_to_search_service = f"{row['NE']}:C{s_vlan_final}"
                elif s_vlan_final[0] == 'C':
                    object_name_to_search_service = f"{row['NE']}:{s_vlan_final}"
                elif s_vlan_final[0] == 'S':
                    object_name_to_search_service = f"{row['NE']}:{s_vlan_final.split('.')[0]}"

                # Search for service name
                filtered_row = service_name_df[service_name_df['Object Name'] == object_name_to_search_service]
                print(filtered_row.head())
                if len(filtered_row) > 1:
                    print("Error: Multiple Service names")
                final_services_df['Service Name'].append(
                    ', '.join(filtered_row['VLAN Name'].fillna('NA').astype(str).values))

                # OLT INFO Node IP, OLT Location, OLT Model
                filtered_olt_row = olt_info_df[olt_info_df['Object Name'] == row['NE']]
                final_services_df['Node IP'].append(str(filtered_olt_row['IP Address'].values[0]))
                final_services_df['OLT Location'].append(str(filtered_olt_row['Alias Name'].values[0]))
                olt_model = str(filtered_olt_row['Subrack Model'].values[0])
                final_services_df['OLT Model'].append(olt_model)

                # Uplink info
                modified_svlan = f"C{s_vlan_final}" if isinstance(s_vlan_final, int) else f"C{s_vlan_final.split('.')[0][1:]}" if s_vlan_final[0] == 'S' else s_vlan_final
                if olt_model == 'FX-4':
                    olt_svlan_combine = f"{row['NE']}:IHUB:SV{modified_svlan}"
                    filtered_fx_uplink_row = uplink_port_df[uplink_port_df['Object Name'].str.contains(olt_svlan_combine)]
                    if not filtered_fx_uplink_row.empty:
                        final_services_df['Uplink Port'].append(filtered_fx_uplink_row['SAP ID'].values[-1])
                    else:
                        final_services_df['Uplink Port'].append(None)
                else:
                    filtered_uplink_row = services_info_df[services_info_df['Object Name'].str.contains(row['NE']) & services_info_df['Object Name'].str.contains(modified_svlan)]
                    print(filtered_uplink_row)
                    if not filtered_uplink_row.empty:
                        final_services_df['Uplink Port'].append(str(filtered_uplink_row['@EFM Bridge Port/Virtual UNI/...'].values[0].split(':')[1]))
                    else:
                        final_services_df['Uplink Port'].append(None)

                # ONT INFO, ONT Serial No, ONT Model, ONT Location, Pon Port
                filtered_ont_row = ont_info_df[ont_info_df['Object Name'] == f"{row['NE']}:{ont_id}"]
                final_services_df['ONT Serial Number'].append(str(filtered_ont_row['Serial Number'].values[0]))
                final_services_df['ONT Model'].append(str(filtered_ont_row['Equipped ID'].values[0]))
                final_services_df['ONT Location'].append(str(filtered_ont_row['Description (Part 1)'].values[0]))
                final_services_df['Pon Port'].append(int(filtered_ont_row['PON Port'].values[0]))

                olt_name_ont_port_combine = f"{row['NE']}:{ont_port_value[4:]}"

                # Upstream Profile Name
                filtered_upstream_profile_name_row = ont_upload_bw_df[ont_upload_bw_df['Object Name'].str.contains(olt_name_ont_port_combine)]
                upstream_profile_names = [element for element in filtered_upstream_profile_name_row['Bandwidth Profile'].values if element != '-None-']
                joined_upstream_profile_names = ', '.join(upstream_profile_names)
                final_services_df['Upstream Profile Name'].append(joined_upstream_profile_names)

                # Downstream Profile Name
                filtered_downstream_profile_name_row = ont_download_bw_df[ont_download_bw_df['Object Name'].str.contains(olt_name_ont_port_combine)]
                downstream_profile_names = [element for element in filtered_downstream_profile_name_row['Shaper Profile'].values if element != '-None-']
                joined_downstream_profile_names = ', '.join(downstream_profile_names)
                final_services_df['Downstream Profile Name'].append(joined_downstream_profile_names)

                # Upstream Max Bandwidth, Upstream Assured Bandwidth, Upstream Fixed Bandwidth
                upstream_max_bw = []
                upstream_assured_bw = []
                upstream_fixed_bw = []
                for upstream_profile_name in upstream_profile_names:
                    filtered_upload_bw_row = olt_upload_bw_df[(olt_upload_bw_df['Name'] == upstream_profile_name) & (olt_upload_bw_df['NE'] == row['NE'])]
                    for item in filtered_upload_bw_row['Excess Information Rate (kb/s)']:
                        upstream_max_bw.append(f"{str(int(item) / 1000)} ")
                    for item in filtered_upload_bw_row['Assured Information Rate (kb/s)']:
                        upstream_assured_bw.append(f"{str(int(item) / 1000)} ")
                    for item in filtered_upload_bw_row['Committed Information Rate (kb/s)']:
                        upstream_fixed_bw.append(f"{str(int(item) / 1000)} ")

                # DownstreamPIR / CIR — CHANGED: matched per-profile against
                # olt_download_bw_df (previously matched only by NE against
                # olt_upload_bw_df, so every service on an OLT silently got
                # the same — wrong — upstream value). Now mirrors the
                # Upstream loop above, and divides by 1000 as requested.
                # NOTE: assumes olt_download_bw_df has 'Name', 'NE',
                # 'Excess Information Rate (kb/s)' (-> PIR) and
                # 'Committed Information Rate (kb/s)' (-> CIR) columns,
                # matching olt_upload_bw_df's schema — please confirm these
                # column names against the actual file if this errors out.
                downstream_pir_values = []
                downstream_cir_values = []
                for downstream_profile_name in downstream_profile_names:
                    filtered_download_bw_row = olt_download_bw_df[
                        (olt_download_bw_df['Name'] == downstream_profile_name) & (olt_download_bw_df['NE'] == row['NE'])
                    ]
                    for item in filtered_download_bw_row['Excess Information Rate (kb/s)']:
                        downstream_pir_values.append(str(round(int(item) / 1000, 2)))
                    for item in filtered_download_bw_row['Committed Information Rate (kb/s)']:
                        downstream_cir_values.append(str(round(int(item) / 1000, 2)))

                final_services_df['DownstreamPIR'].append(', '.join(downstream_pir_values) if downstream_pir_values else None)
                final_services_df['DownstreamCIR'].append(', '.join(downstream_cir_values) if downstream_cir_values else None)

                final_services_df['Upstream Max Bandwidth'].append(', '.join(map(str, upstream_max_bw)))
                final_services_df['Upstream Assured Bandwidth'].append(', '.join(map(str, upstream_assured_bw)))
                final_services_df['Upstream Fixed Bandwidth'].append(', '.join(map(str, upstream_fixed_bw)))

final_services_df = pd.DataFrame(final_services_df)

# Rearrange columns
final_services_df = final_services_df[['Vendor', 'Package', 'OLT Hostname', 'OLT Location', 'ONT Port', 'Service Name', 'Service Type', 'Uplink Port', 'SVLAN', 'Traffic Type',
         'Node IP', 'CVLAN', 'Upstream Profile Name', 'Downstream Profile Name', 'ONT ID', 'ONT Serial Number', 'ONT Location',
         'ONT Model', 'Pon Port', 'OLT Model', 'Upstream Max Bandwidth', 'Upstream Assured Bandwidth', 'Upstream Fixed Bandwidth', 'DownstreamPIR', 'DownstreamCIR']]

final_services_df.to_excel('Reports/NokiaServices.xlsx', engine='openpyxl', index=False)
