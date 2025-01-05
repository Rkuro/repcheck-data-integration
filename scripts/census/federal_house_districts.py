"""
This script is intended to download the federal house districts (CD) from the census.gov
source and ingest into postgres
"""

import shapefile
import logging
import requests
import os
import zipfile
from sqlalchemy.sql import func
import json
import shutil

from scripts.census.census_utils import district_number_helper
from scripts.database.database import upsert_dynamic, get_session
from scripts.database.models import Area
from scripts.reference_data_helper import get_fips_state_mapping
from ..logging_config import setup_logging

log = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.getcwd(), '_data', "federal_house_districts")


def download_congressional_district_data(file_number):
    download_base_url = "https://www2.census.gov/geo/tiger/TIGER2024/CD/"

    # Once every two years we will need to update this to input the new congress
    zip_filepath = os.path.join(DATA_DIR, f"tl_2024_{file_number}_cd119.zip")

    # Ex. https://www2.census.gov/geo/tiger/TIGER2024/CD/tl_2024_01_cd119.zip
    download_url = download_base_url + f"tl_2024_{file_number}_cd119.zip"

    response = requests.get(download_url)

    # Blunt way of handling skipped fips codes by the census
    if response.status_code == 404:
        return

    response.raise_for_status()

    with open(zip_filepath, "wb") as f:
        f.write(response.content)

    with zipfile.ZipFile(zip_filepath, "r") as zip_ref:
        zip_ref.extractall(DATA_DIR)
        """
        This should include the following files:
        tl_2024_$num_cd119.cpg
        tl_2024_$num_cd119.dbf
        tl_2024_$num_cd119.prj
        tl_2024_$num_cd119.shp
        tl_2024_$num_cd119.shp.ea.iso.xml
        tl_2024_$num_cd119.shp.iso.xml
        tl_2024_$num_cd119.shx
        """

    shapefile_path = os.path.join(DATA_DIR, f"tl_2024_{file_number}_cd119.shp")
    sf = shapefile.Reader(shapefile_path)

    num_records = len(sf.records())

    fips_mapping = get_fips_state_mapping()

    for i in range(num_records):
        record = sf.record(i)
        shape = sf.shape(i)

        state_fips_code = record[0]

        # Sorry puerto rico et al
        if state_fips_code not in fips_mapping:
            continue

        if record[1] == "ZZ":
            # Undefined district numbers exist for some reason...
            continue

        classification = "federal_house_district"
        state_info = fips_mapping[state_fips_code]
        district_number = district_number_helper(classification, state_info, record[1])

        if state_info["abbreviation"] in ["AK", "DE", "ND", "SD", "VT", "WY"]:
            log.info(f"Using at-large district - {state_info['abbreviation']} -  {district_number}")

        # Cuz DC is not a state :sigh:
        if state_info["abbreviation"] in ["DC"]:
            ocd_id = f"ocd-division/country:us/district:{state_info.get('abbreviation').lower()}/cd:{district_number.lower()}"
        else:
            ocd_id = f"ocd-division/country:us/state:{state_info.get('abbreviation').lower()}/cd:{district_number.lower()}"

        yield Area(
            id=ocd_id,
            classification=classification,
            name=f"{state_info.get('name')} {record[4]}",
            abbrev=None,
            fips_code=state_fips_code,
            district_number=district_number,
            geo_id=record[2],
            geo_id_fq=record[3],
            legal_statistical_area_description_code=record[5],
            maf_tiger_feature_class_code=record[7],
            funcstat=record[8],
            land_area=record[9],
            water_area=record[10],
            centroid_lat=float(record[11]),
            centroid_lon=float(record[12]),
            geometry=func.ST_GeomFromGeoJSON(json.dumps(shape.__geo_interface__))
        )


def cleanup():
    pass

def main():

    log.info("Downloading federal house districts")

    # Setup
    session = get_session()
    os.makedirs(DATA_DIR, exist_ok=True)

    # there are 78 congressional district zip files that are numbered by their state FIPS code
    # however the census skips some e.g. virgin islands or the canal zone because they don't have true congressional representatives :yikes:
    numbers = [str(i).zfill(2) for i in range(1, 78)]

    total_ids = []

    for zip_file_number in numbers:
        for area in download_congressional_district_data(zip_file_number):
            upsert_dynamic(session, area)
            total_ids.append(area)
            log.info(f"Completed jurisdiction: {area.name}")

    log.info(f"Areas downloaded {len(total_ids)}")

    cleanup()

    log.info("Finished")

if __name__ == "__main__":
    setup_logging()
    main()