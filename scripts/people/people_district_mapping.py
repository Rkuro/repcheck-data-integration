import os
import csv
import logging
import json
from ..logging_config import setup_logging

log = logging.getLogger(__name__)

def convert_district_name_to_people_format(fips_code, district_name):

    # Massachusetts
    if fips_code == '25':
        district_name = district_name.replace("Massachusetts", "")
        district_name = district_name.replace("District", "")
        return district_name.strip()

    raise RuntimeError(f"Unimplemented fips code {fips_code}")

def main():

    mapping = {}
    with open("/Users/robinkurosawa/git/repcheck-data-integration/output_file.csv", "r") as csvfile:
        reader = csv.DictReader(csvfile)
        for area in reader:
            area_id = area["id"]
            fips_code = area["fips_code"]
            area_name = area["name"]

            district_name = convert_district_name_to_people_format(fips_code, area_name)

            log.info(f"Mapping {area_name} to people format - {district_name}")

            mapping[district_name] = area_id
    with open("/reference_data/state_people_district_mapping.json", "w") as outfile:
        json.dump(mapping, outfile, indent=4)

if __name__ == '__main__':
    setup_logging()
    main()