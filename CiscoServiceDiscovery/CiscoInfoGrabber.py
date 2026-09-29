import command_output_converter
from netmiko import ConnectHandler

class CiscoInfoGrabber:
    def __init__(self, ip):
        self.RouterIp = ip
        self.net_connect = None
        self.error = None

        try:
            cisco_device = {
                'device_type': 'cisco_ios',
                'host': self.RouterIp,
                'username': 'govindareddy.b',
                'password': 'J!f@b&r&987654',
            }
            self.net_connect = ConnectHandler(**cisco_device)
            self.net_connect.enable()
            self.chassis_info = command_output_converter.chassis_info_converter(self.self_send_command('show inventory'), self.RouterIp)
            self.hostname = command_output_converter.hostname_converter(self.self_send_command('show running-config | include hostname'), self.RouterIp)
            self.vrf = command_output_converter.vrf_converter(self.self_send_command('sh vrf'), self.RouterIp)
            self.all_bridge_domains = []
            self.bridge_domain_info = {}
            self.port_channels = {}

            for bd in self.vrf:
                if len(bd['Interfaces']) > 1:
                    for each_bd in bd['Interfaces'][1:]:
                        if each_bd[0] == 'B':
                            self.all_bridge_domains.append(each_bd)
                            self.port_channels.update({each_bd : command_output_converter.port_channel_finder_with_bd(self.self_send_command(f'sh bridge-domain {each_bd[2:]}'), self.RouterIp)})
                            self.bridge_domain_info.update({each_bd : command_output_converter.bridge_domain_info(self.self_send_command(f'show int {each_bd}'))})
                elif len(bd['Interfaces']) == 1:
                    self.all_bridge_domains.append(bd['Interfaces'][0])
                    self.port_channels.update({bd['Interfaces'][0]: command_output_converter.port_channel_finder_with_bd(self.self_send_command(f'sh bridge-domain {bd['Interfaces'][0][2:]}'), self.RouterIp)})
                    self.bridge_domain_info.update({bd['Interfaces'][0]: command_output_converter.bridge_domain_info(self.self_send_command(f'show int {bd['Interfaces'][0]}'))})

            self.all_port_channels = list(set(value for value in self.port_channels.values() if 'port-channel' in value.lower()))
            self.port_channel_status = [{item : command_output_converter.port_channel_info(self.self_send_command(f'show int {item}'), self.RouterIp)} for item in self.all_port_channels]
            self.port_channel_info = [{item: command_output_converter.port_channel_run_interface_info(self.self_send_command(f'show run interface {item}'), self.RouterIp)} for item in self.all_port_channels]
            self.l3vpn_info = [{item['service_name']: command_output_converter.l3vpn_converter(self.self_send_command(f'show run vrf {item['service_name']}'))} for item in self.vrf]
            self.olt_connected_bd_ports = command_output_converter.olt_bd_info_finder(self.self_send_command('sho int des | inc OLT'))
            self.connected_olt_ip = {}
            for bd in self.olt_connected_bd_ports:
                self.connected_olt_ip.update(command_output_converter.connected_olt_ip(self.self_send_command(f'sho arp vrf  TFIBER-IP-MGMT | inc BDI{bd[2:]}'), bd))
            self.cdp_nei = command_output_converter.cdp_neighbours_info(self.self_send_command('show cdp neighbors'))
            self.disconnect()
        except Exception as e:
            # print(f'Cannot connect to the {ip}: {e}')
            self.net_connect = None
            self.error = e

    def disconnect(self):
        if self.net_connect:
            self.net_connect.disconnect()

    def self_send_command(self, command):
        if self.net_connect:
            return self.net_connect.send_command(command)
        return None

    def get_router_info(self):
        if self.net_connect is not None:
            return {
                'Router IP': self.RouterIp,
                'Chassis Information': self.chassis_info,
                'Hostname' : self.hostname,
                'Vrf Information': self.vrf,
                'Total Bridge Domains': self.all_bridge_domains,
                'Bridge Domain Status': self.bridge_domain_info,
                'Port-Channels Information': self.port_channels,
                'Total Port Channels': self.all_port_channels,
                'Port Channel Status': self.port_channel_status,
                'Port Channel Information': self.port_channel_info,
                'L3VPN Information': self.l3vpn_info,
                'Connected OLT IP': self.connected_olt_ip,
                'CDP Neighbors': self.cdp_nei,
            }
        else:
            return {
                'Router IP': self.RouterIp,
                'Connection Error': str(self.error)
            }

