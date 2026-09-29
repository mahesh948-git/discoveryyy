class ServiceObjectMaker:
    def __init__(self, data):
        self.vendor = "TEJAS"
        self.connectivity_service = self.extract_connectivity_service(data)
        self.uuid = data['connectivity-service'].get('uuid', None)
        self.operational_state = data['connectivity-service'].get('operational-state', None)
        self.lifecycle_state = data['connectivity-service'].get('lifecycle-state', None)
        self.administrative_state = data['connectivity-service'].get('administrative-state', None)
        self.status = self.extract_value_from_addinfo(data, 'Status')
        self.config_state = self.extract_value_from_addinfo(data, 'ConfigState')
        self.associated_vlan = self.extract_value_from_addinfo(data, 'associated-vlans')
        self.customer = self.extract_value_from_addinfo(data, 'Customer')
        self.gpon_service_type = self.extract_value_from_addinfo(data, 'GPONServiceType')
        self.gpon_type = self.extract_value_from_addinfo(data, 'GPONType')
        self.status_msg = self.extract_value_from_addinfo(data, 'StatusMsg')
        self.end_points = int(len(data['connectivity-service'].get('end-point', [])))
        self.end_point_data = data['connectivity-service'].get('end-point')

    def extract_value_from_addinfo(self, data, value_name):
        additional_info = data['connectivity-service'].get('additional-information', [])
        for item in additional_info:
            if item.get('value-name') == value_name:
                return item.get('value')
        return None

    def extract_connectivity_service(self, data):
        name = data['connectivity-service'].get('name', [])
        for item in name:
            if item.get('value-name') == 'ConnectivityService':
                return item.get('value')
        return None

    def __repr__(self):
        return (
            f'OLTDetails('
            f"connectivity-service: {self.connectivity_service},  uuid: {self.uuid},  operatinol-state: {self.operational_state}\n"
            f"lifecycle_state: {self.lifecycle_state}, administrative_state: {self.administrative_state}\n"
            f"config_state: {self.config_state},  status: {self.status}\n"
            f"associated_vlan: {self.associated_vlan}, customer: {self.customer}, gpon_service_type: {self.gpon_service_type}\n"
            f"gpon_type: {self.gpon_type}, status_msg: {self.status_msg}, end_point: {self.end_points} \n\n ........."
        )

class EndPointsObjectMaker:
    def __init__(self, data, downstream_lookup=None):
        endpoints = data.get('connection-end-point')

        if isinstance(endpoints, list) and len(endpoints) > 0:
            endpoint0 = endpoints[0]
            self.node_uuid = endpoint0.get('node-uuid')
            self.edge_point_uuid = endpoint0.get('node-edge-point-uuid')
        else:
            self.node_uuid = None
            self.edge_point_uuid = None

        self.serial_number = self.extract_value_from_addinfo(data, 'serial-number')
        self.port_label = self.extract_value_from_addinfo(data, 'port-label')
        self.ont_eth_port_instance = self.extract_value_from_addinfo(data, 'ONTEthPortInstance')
        self.node_admin_status = self.extract_value_from_addinfo(data, 'NodeAdminStatus')
        self.v_lan_id = self.extract_vlan_id(data)
        self.s_vlan_id = self.extract_s_vlan_id(data)
        self.ingress_vlan1 = self.extract_value_from_addinfo(data, 'ingress-vlan1')
        self.cos_name = self.extract_cos_name(data)
        self.life_cycle_state = data.get('lifecycle-state', None)
        self.traffic_type = self.extract_value_from_addinfo(data, 'TrafficType')
        self.ep_type = self.extract_value_from_addinfo(data, 'ep-type')
        self.traffic_origin = self.extract_value_from_addinfo(data, 'TrafficOrigin')
        self.upstream_bandwidth_profile_name = None
        self.downstream_bandwidth_profile_name = None

        upstream_bandwidth_profile = data.get('upstream-bandwidth-profile', None)
        if isinstance(upstream_bandwidth_profile, dict):
            self.upstream_bandwidth_profile_name = upstream_bandwidth_profile.get('upstream-bandwidth-profile-uuid', None)

        downstream_bandwidth_profile = data.get('downstream-bandwidth-profile', None)
        if isinstance(downstream_bandwidth_profile, dict):
            self.downstream_bandwidth_profile_name = downstream_bandwidth_profile.get('downstream-bandwidth-profile-uuid', None)

        # --- NEW: resolve DownstreamPIR/CIR directly from the profile catalog ---
        # PIR = peak-information-rate, CIR = committed-information-rate (standard convention).
        # downstream_lookup is Tejas-only by construction (this whole class only ever
        # parses Tejas services.json), so there is no risk of matching a Nokia profile
        # of the same name against the wrong catalog.
        self.downstream_pir = None
        self.downstream_cir = None
        if downstream_lookup and self.downstream_bandwidth_profile_name:
            profile_rates = downstream_lookup.get(self.downstream_bandwidth_profile_name)
            if profile_rates:
                self.downstream_pir = profile_rates.get('peak_information_rate')
                self.downstream_cir = profile_rates.get('committed_information_rate')

    def extract_value_from_addinfo(self, data, value_name):
        name = data.get('additional-information', [])
        for item in name:
            if item.get('value-name') == value_name:
                return item.get('value')
        return None

    def extract_vlan_id(self, data):
        try:
            vlan_info = data['nrp-carrier-eth-connectivity-end-point-resource']['ce-vlan-id-list-and-untag']['vlan-id']
            if vlan_info:
                return vlan_info[0].get('vlan-id', 'NA')
        except (KeyError, IndexError, TypeError):
            return 'NA'
        return 'NA'

    def extract_s_vlan_id(self, data):
        try:
            s_vlan_info = data['nrp-carrier-eth-connectivity-end-point-resource']['s-vlan-id-list']['vlan-id-list']
            if s_vlan_info:
                return s_vlan_info[0].get('vlan-id', 'NA')
        except (KeyError, IndexError, TypeError):
            return 'NA'
        return 'NA'

    def extract_cos_name(self, data):
        try:
            cos_info = data['nrp-carrier-eth-connectivity-end-point-resource']['cos-identifier-list']
            if cos_info:
                return cos_info[0].get('cos-name', None)
        except (KeyError, IndexError, TypeError):
            return None
        return None