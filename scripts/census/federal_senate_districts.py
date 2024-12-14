"""
This script is intended to download the federal senate districts (STATE) from the census.gov
source and ingest into postgres
"""
import shapefile
import logging
import requests
import os
import zipfile
import json
from sqlalchemy.sql import func
import shutil

from scripts.database.database import get_session, upsert_dynamic
from scripts.database.models import Jurisdiction
from scripts.fips_helper import get_fips_state_mapping
from ..logging_config import setup_logging

log = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.getcwd(), '_data', "federal_senate_districts")


def download_state_data():
    # There's only a single file needed for state boundaries cuz there's so few of them
    download_url = "https://www2.census.gov/geo/tiger/TIGER2024/STATE/tl_2024_us_state.zip"

    zip_filepath = os.path.join(DATA_DIR, 'tl_2024_us_state.zip')
    with open(zip_filepath, "wb") as f:
        f.write(requests.get(download_url).content)

    with zipfile.ZipFile(zip_filepath, "r") as zip_ref:
        zip_ref.extractall(DATA_DIR)
        """
        This should include the following files:
        tl_2024_us_state.cpg
        tl_2024_us_state.dbf
        tl_2024_us_state.prj
        tl_2024_us_state.shp
        tl_2024_us_state.shp.ea.iso.xml
        tl_2024_us_state.shp.iso.xml
        tl_2024_us_state.shx
        """

    shapefile_path = os.path.join(DATA_DIR, 'tl_2024_us_state.shp')
    sf = shapefile.Reader(shapefile_path)

    num_records = len(sf.records())

    fips_mapping = get_fips_state_mapping()

    for i in range(num_records):
        record = sf.record(i)
        shape = sf.shape(i)

        state_fips_code = record[2]

        # Sorry puerto rico et al :(
        if state_fips_code not in fips_mapping:
            continue
        state_info = fips_mapping[state_fips_code]

        ocd_id = f"ocd-jurisdiction/country:us/state:{state_info.get('abbreviation').lower()}/government"

        yield Jurisdiction(
            id=ocd_id,
            classification="federal_senate_district",
            name=f"{state_info.get('name')}",
            abbrev=state_info.get('abbreviation'),
            fips_code=state_fips_code,
            district_number=None,
            geo_id=state_fips_code,
            geo_id_fq=record[5],
            legal_statistical_area_description_code=record[8],
            maf_tiger_feature_class_code=record[9],
            funcstat=record[10],
            land_area=record[11],
            water_area=record[12],
            centroid_lat=float(record[13]),
            centroid_lon=float(record[14]),
            geometry=func.ST_GeomFromGeoJSON(json.dumps(shape.__geo_interface__)),
        )


def cleanup():
    shutil.rmtree(DATA_DIR)

def main():

    log.info("Downloading federal senate districts")

    # Setup
    session = get_session()
    os.makedirs(DATA_DIR, exist_ok=True)

    total_ids = []
    # There is only a single state zip file
    for jurisdiction in download_state_data():
        upsert_dynamic(session, jurisdiction)
        total_ids.append(jurisdiction.id)
        log.info(f"Completed jurisdiction {jurisdiction.name}")

    log.info(f"Jurisdictions downloaded {len(total_ids)}")

    cleanup()

    log.info("Finished")

if __name__ == "__main__":
    setup_logging()
    main()