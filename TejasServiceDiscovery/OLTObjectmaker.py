import json

#### Takes each row from OLT json and converts to Objects of each value.
class OLTObjectMaker:
    def __init__(self, data, package):
        self.vendor = 'TEJAS'
        self.pacakge = f"Package-{package}"
        self.device = "OLT"
        self.district = self.extract_value_from_addinfo(data, 'partition')[:-9]
        self.location = self.extract_value_from_addinfo(data, 'location')[6:]
        self.olt_ip = self.extract_managed_element(data)
        self.olt_name = self.extract_value_from_addinfo(data, 'nativeEMSName')
        self.product_name = self.extract_value_from_addinfo(data, 'productName')
        self.description = self.extract_value_from_addinfo(data, 'Descr')
        self.snmp_encryption_algorithm = self.extract_value_from_addinfo(data, 'snmpv3EncryptionAlgorithm')
        self.comm_protocol = self.extract_value_from_addinfo(data, 'commprotocol')
        self.upgraded_software_version = self.extract_value_from_addinfo(data, 'UpgradedSoftwareVersion')
        self.ethernet_ip = self.extract_value_from_addinfo(data, 'EthernetIP')
        self.num_of_ont_connected = f"{self.extract_available_open_ports(data, package)} ONT{'s' if self.extract_available_open_ports(data, package) != 1 else ''} connected"
        self.operational_status = data.get('operational-state', None)
        self.admin_status = data.get('administrative-state', None)
        self.physical_comm_status = self.extract_value_from_addinfo(data, 'commState')
        self.creation_time = self.extract_value_from_addinfo(data, 'creationTime')
        self.last_up_time = self.extract_value_from_addinfo(data, 'LastNodeUpTime')
        self.last_down_time = self.extract_value_from_addinfo(data, 'LastNodeDownTime')
        self.modify_time = self.extract_value_from_addinfo(data, 'modifyTime')
        self.last_available_time = self.extract_value_from_addinfo(data, 'LastNodeAvailableTime')
        self.node_endpoints = len(data.get('node-edge-point', []))
        self.connected_ports = self.extract_port_list(data, package)

    def extract_value_from_addinfo(self, data, value_name):
        additional_info = data.get('additional-information', [])
        for item in additional_info:
            if item.get('value-name') == value_name:
                return item.get('value')
        return None

    def extract_pacakge(self, data):
        location = self.extract_value_from_addinfo(data, "location")
        if location and 'PKG-' in location:
            return location.split('-')[1] if "-" in location else None
        return None

    def extract_managed_element(self, data):
        names = data.get('name', [])
        for item in names:
            if item.get('value-name') == 'ManagedElement':
                return item.get('value')
        return None

    def extract_port_list(self, data, pkg):
        try:
            ip = self.extract_managed_element(data)
            filename = f"Tejaspackage(API_responses)/TejasPkg{pkg}ont_count.json"
            with open(filename, 'r') as file:
                return ','.join([s.split('|')[-2].split('-')[-1] for s in json.load(file) if s.split('|')[1] == ip])
        except Exception as e:
            print(f"An error occurred: {e}")
            return "NA"

    def extract_available_open_ports(self, data, pkg):
        try:
            ip = self.extract_managed_element(data)
            filename = f"Tejaspackage(API_responses)/TejasPkg{pkg}ont_count.json"
            with open(filename, 'r') as file:
                data = json.load(file)
                data = [item.split('|')[1] for item in data]
                return data.count(ip)
        except Exception as e:
            # Log the error if needed
            print(f"An error occurred: {e}")
            return "NA"

    def __repr__(self):
        return (
            f'OLTDetails('
            f"package: {self.pacakge},  district: {self.district},  Location: {self.location}\n"
            f"open ports: {self.num_of_ont_connected}, ports connected on: {self.connected_ports}\n"
            f"olt_ip: {self.olt_ip},  olt_name: {self.olt_name}\n"
            f"Ops-status: {self.operational_status}, Admin-status: {self.admin_status}, Physical-status: {self.physical_comm_status}\n"
            f"Node-Endpoints: {self.node_endpoints} ....\n\n"
        )

