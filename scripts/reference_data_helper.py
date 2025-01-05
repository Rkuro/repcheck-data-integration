import os
from pathlib import Path
import json

def get_fips_state_mapping():
    current_fpath = Path(__file__)

    fips_path = os.path.join(current_fpath.parent.parent, 'reference_data', 'state_fips.json')

    with open(fips_path) as json_f:
        return json.load(json_f)

def get_state_district_mapping():
    current_fpath = Path(__file__)

    district_mapping_path = os.path.join(current_fpath.parent.parent, 'reference_data', 'state_people_district_mapping.json')

    with open(district_mapping_path) as json_f:
        return json.load(json_f)