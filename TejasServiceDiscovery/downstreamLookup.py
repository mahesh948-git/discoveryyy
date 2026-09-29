import json

# Package -> Tejas NMS endpoint (used only to know which JSON file to read;
# actual fetching is handled by whatever already writes these files, e.g.
# response_grabber() using token_grabber()).
PKGS = ['A', 'B', 'C']


def downstream_profile_lookup(pkgs=None):
    """
    Builds {profile_name: {'committed_information_rate': value, 'peak_information_rate': value}}
    from Tejaspackage(API_responses)/TejasPkg{pkg}downstream.json for each package.

    Values are divided by 1000 from the raw API units (matching the same
    /1000 convention Upstream already uses), with no unit text appended —
    just the numeric value.

    NOTE: this is intentionally Tejas-only — do not reuse this lookup against
    Nokia rows. Profile names can collide by coincidence across vendors
    (e.g. both having a profile literally named "DN_TDIA_4M") while pointing
    at completely different actual rates.
    """
    if pkgs is None:
        pkgs = PKGS

    lookup = {}
    for pkg in pkgs:
        file_name = f'Tejaspackage(API_responses)/TejasPkg{pkg}downstream.json'
        try:
            with open(file_name, 'r') as file:
                all_data = json.load(file)
        except FileNotFoundError:
            print(f"⚠️ {file_name} not found — skipping package {pkg} for downstream lookup.")
            continue

        parsed_count = 0
        for item in all_data:
            profile = item.get('downstream-bandwidth-profile', item) if isinstance(item, dict) else item

            committed_raw = (profile.get('committed-information-rate') or {}).get('value')
            peak_raw = (profile.get('peak-information-rate') or {}).get('value')
            committed = round(committed_raw / 1000, 2) if committed_raw is not None else None
            peak = round(peak_raw / 1000, 2) if peak_raw is not None else None
            values = {
                'committed_information_rate': committed,
                'peak_information_rate': peak,
            }

            # KEY CHANGE: services.json stores a uuid reference
            # (downstream-bandwidth-profile-uuid), NOT profile-name — and uuid is
            # not reliably derivable from profile-name (e.g. uuid "Default" vs
            # profile-name "Default Shaper"). So key on uuid, stripping the
            # "TejNMS-" prefix when present since the service-side field doesn't
            # carry it. Also keep profile-name as a secondary key, in case some
            # service objects reference it by name instead of uuid.
            uuid_val = profile.get('uuid')
            if uuid_val:
                bare_uuid = uuid_val[len('TejNMS-'):] if uuid_val.startswith('TejNMS-') else uuid_val
                lookup[bare_uuid] = values
                parsed_count += 1

            name = profile.get('profile-name')
            if name and name not in lookup:
                lookup[name] = values

        print(f"  ✅ Package {pkg}: parsed {parsed_count} downstream profiles from {file_name} ({len(all_data)} raw entries).")

    print(f"Downstream lookup built: {len(lookup)} total keys. Sample keys: {list(lookup.keys())[:8]}")
    return lookup