import os
from pathlib import Path
import json

def get_fips_state_mapping():
    current_fpath = Path(__file__)

    fips_path = os.path.join(current_fpath.parent.parent, 'reference_data', 'state_fips.json')

    with open(fips_path) as fips_file:
        return json.load(fips_file)