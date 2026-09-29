from downstreamLookup import downstream_profile_lookup

lookup = downstream_profile_lookup()
print(len(lookup))

# check specific values you know from your report
for key in ['DN_GI_30M', 'DN_TNET_GI_50Mb', 'DN_UPS-MGMT']:
    print(key, '->', lookup.get(key))