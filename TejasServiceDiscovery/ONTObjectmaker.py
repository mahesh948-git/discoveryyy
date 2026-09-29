import json
import  math

class ONTObjectMaker:
    def __init__(self, data, package):
        self.vendor = 'TEJAS'
        self.pacakge = f"Package-{package}"
        self.device = "ONT"
        self.location = self.extract_value_from_addinfo(data, 'Location')
        # self.ont_uuid = data['remote-unit']['ont'].get('uuid', None)
        self.ont_uuid = data.get('remote-unit', {}).get('ont', {}).get('uuid', None)
        self.EquipmentHolder = self.extract_value_from_name(data, 'EquipmentHolder')
        equipment_holder = self.extract_value_from_name(data, 'EquipmentHolder') or ''
        parts = equipment_holder.split('/')
        self.slot = parts[1].split('-')[-2] if len(parts) > 1 and '-' in parts[1] else None
        self.shelf = parts[2].split('=')[-1] if len(parts) > 2 and '=' in parts[2] else None
        self.pon_port = parts[1].split('-')[-1] if len(parts) > 1 and '-' in parts[1] else None
        self.nativeEMSName = self.extract_value_from_addinfo(data, 'nativeEMSName')
        self.EquipmentId = self.extract_value_from_addinfo(data, 'EquipmentId')
        self.SerialNo = self.extract_value_from_addinfo(data, 'SerialNo')
        self.ManagedElement = self.extract_value_from_name(data, 'ManagedElement')# parent ID
        self.AdminState = self.extract_value_from_addinfo(data, 'AdminState')
        self.PhysicalStatus = self.extract_value_from_addinfo(data, 'PhysicalStatus')
        self.PMStatus = self.extract_value_from_addinfo(data, 'PMStatus')
        self.IsDuplicate = self.extract_value_from_addinfo(data, 'IsDuplicate')
        self.Mode = self.extract_value_from_addinfo(data,'Mode')
        self.Distance = f"{round(int(self.extract_value_from_addinfo(data, 'Distance')) / 1000, 2)} Km" if self.extract_value_from_addinfo(data, 'Distance') != None else None
        self.TotalGemPortIds = self.extract_value_from_addinfo(data, 'TotalGemPortIds')
        self.VendorId = self.extract_value_from_addinfo(data, 'VendorId')
        self.LastONTGUnavailableTime = self.extract_value_from_addinfo(data, 'LastONTGUnavailableTime')
        self.LastONTGAvailableTime = self.extract_value_from_addinfo(data, 'LastONTGAvailableTime')
        self.NodeCreateTime = self.extract_value_from_addinfo(data, 'NodeCreateTime')
        self.NodeModifyTime = self.extract_value_from_addinfo(data, 'NodeModifyTime')
        self.SwVersion = self.extract_value_from_addinfo(data, 'SwVersion')
        self.ActiveSwVersion = self.extract_value_from_addinfo(data, 'ActiveSwVersion')
        self.MACAddress = self.extract_value_from_addinfo(data, 'MACAddress')
        self.NumCards = self.extract_value_from_addinfo(data, 'NumCards')
        self.associated_max_bandwidth = self.extract_value_from_addinfo(data, 'associated-max-bandwidth')
        self.associated_assured_bandwidth = self.extract_value_from_addinfo(data, 'associated-assured-bandwidth')
        self.associated_fixed_bandwidth = self.extract_value_from_addinfo(data, 'associated-fixed-bandwidth')
        self.associated_outer_vlan = self.extract_value_from_addinfo(data, 'associated-outer-vlan')
        self.associated_translated_vlan = self.extract_value_from_addinfo(data, 'associated-translated-vlan')
        self.total_node_edge_point = len(data.get('remote-unit', {}).get('node-edge-point', []) or [])

    def __repr__(self):
        return (
            f'ONTDetails(' 
            f"ont_uuid: {self.ont_uuid},  EquipmentHolder: {self.EquipmentHolder},  Location: {self.location}\n"
            f"Splited_Equitment_Holder: {self.EquipmentHolder.split('/')}, Distance: {self.Distance}"
            f"slot: {self.slot}, shelf: {self.shelf}\n"
            f"pon_port: {self.pon_port},  nativeEMSName: {self.nativeEMSName}\n"
            f"ManagedElement: {self.ManagedElement}, total_node_edge_point: {self.total_node_edge_point}, LastONTGUnavailableTime: {self.LastONTGUnavailableTime}\n"
            f" ....\n\n"
        )

    def extract_value_from_addinfo(self, data, value_name):
        additional_info = (
            data.get('remote-unit', {})
            .get('ont', {})
            .get('additional-information', [])
        )
        for item in additional_info:
            if item.get('value-name') == value_name:
                return item.get('value', None)
        return None

    def extract_value_from_name(self, data, value_name):
        name_info = (
            data.get('remote-unit', {})
            .get('ont', {})
            .get('name', [])
        )
        for item in name_info:
            if item.get('value-name') == value_name:
                return item.get('value', None)  # Returns None if key missing
        return None












