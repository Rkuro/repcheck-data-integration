"""
This script is intended to download the state senate districts aka
"State Legislative District Upper" (SLDU) from the census.gov
source and ingest into postgres
"""
from collections import Counter

import shapefile
import logging
import requests
import os
import zipfile
import shutil
from typing import Generator
from sqlalchemy.sql import func
import json

from ..database.models import Area
from ..database.database import get_session, upsert_dynamic
from ..logging_config import setup_logging
from ..fips_helper import get_fips_state_mapping
from .census_utils import district_number_helper

log = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.getcwd(), '_data', "state_senate_districts")


def download_state_district_data(file_number) -> Generator[Area, None, None]:
    download_base_url = "https://www2.census.gov/geo/tiger/TIGER2024/SLDU/"

    zip_filepath = os.path.join(DATA_DIR, f"tl_2024_{file_number}_sldu.zip")

    # Ex. https://www2.census.gov/geo/tiger/TIGER2024/SLDU/tl_2024_01_sldu.zip
    download_url = download_base_url + f"tl_2024_{file_number}_sldu.zip"

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
        tl_2024_$num_sldu.cpg
        tl_2024_$num_sldu.dbf
        tl_2024_$num_sldu.prj
        tl_2024_$num_sldu.shp
        tl_2024_$num_sldu.shp.ea.iso.xml
        tl_2024_$num_sldu.shp.iso.xml
        tl_2024_$num_sldu.shx
        """

    shapefile_path = os.path.join(DATA_DIR, f"tl_2024_{file_number}_sldu.shp")
    sf = shapefile.Reader(shapefile_path)

    num_records = len(sf.records())

    fips_mapping = get_fips_state_mapping()

    for i in range(num_records):
        record = sf.record(i)
        shape = sf.shape(i)

        if record[1] == "ZZZ":
            # Undefined districts make sense in the case e.g. where the entire district is a body of water
            # idk why they are in the SLDU zip files though...
            log.debug("Skipping undefined district")
            continue

        classification = "state_senate_district"
        state_fips_code = record[0]
        state_info = fips_mapping[state_fips_code]
        district_number = district_number_helper(classification, state_info, record[1])

        if state_info["abbreviation"] == "DC":
            ocd_id = f"ocd-division/country:us/district:dc/ward:{district_number}"
        else:
            ocd_id = f"ocd-division/country:us/state:{state_info.get('abbreviation').lower()}/sldu:{district_number.lower()}"

        yield Area(
            id=ocd_id,
            classification=classification,
            name=f"{state_info.get('name')} {record[4]}", # "Pennsylvania Senate District 1"
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
            geometry=func.ST_GeomFromGeoJSON(json.dumps(shape.__geo_interface__)),
        )


def cleanup():
    shutil.rmtree(DATA_DIR)


def main():

    # Setup
    session = get_session()
    os.makedirs(DATA_DIR, exist_ok=True)

    # There are 72 state district zip files that are numbered by their state FIPS code
    # however the census skips some e.g. virgin islands or the canal zone because they
    # don't have state senates :yikes:
    numbers = [str(i).zfill(2) for i in range(1, 72)]

    total_ids = []

    for zip_file_number in numbers:
        log.info(f"Downloading file {zip_file_number}")
        for area in download_state_district_data(zip_file_number):
            upsert_dynamic(session, area)
            total_ids.append(area.id)
            log.info(f"Completed area {area.name}")

    counts = Counter(total_ids)
    duplicates = [item for item, count in counts.items() if count > 1]

    log.info(f"Areas downloaded {len(total_ids)}. duplicate ids: {duplicates}")

    cleanup()

    log.info("Finished")

if __name__ == "__main__":
    setup_logging()
    main()