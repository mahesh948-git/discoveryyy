import json
import pandas as pd

upstream_bandwidth_df = {
    'profile_name': [],
    'fixed_bandwidth': [],
    'max_bandwidth': [],
    'assured_bandwidth': [],
}

class UpstreamObjectMaker:
    def __init__(self, data):
        self.profile_name = data['upstream-bandwidth-profile'].get('profile-name', 'NA')
        self.fixed_bandwidth = data['upstream-bandwidth-profile'].get('fixed-bandwidth', 'NA')
        self.max_bandwidth = data['upstream-bandwidth-profile'].get('max-bandwidth', 'NA')
        self.assured_bandwidth = data['upstream-bandwidth-profile'].get('assured-bandwidth', 'NA')

def upstream_bandwidth_df_maker():
    pkgs = ['A', 'B', 'C']
    for pkg in pkgs:
        file_name = f'Tejaspackage(API_responses)/TejasPkg{pkg}upstream.json'
        with open(file_name, 'r') as file:
            all_data = json.load(file)
        for data in all_data:
            upstream_obj = UpstreamObjectMaker(data)
            upstream_bandwidth_df['profile_name'].append(upstream_obj.profile_name)
            upstream_bandwidth_df['fixed_bandwidth'].append(f"{round(int(upstream_obj.fixed_bandwidth) / 1000, 2)} ")
            upstream_bandwidth_df['max_bandwidth'].append(f"{round(int(upstream_obj.max_bandwidth) / 1000, 2)} ")
            upstream_bandwidth_df['assured_bandwidth'].append(f"{round(int(upstream_obj.assured_bandwidth) / 1000, 2)} ")

    return pd.DataFrame(upstream_bandwidth_df)

