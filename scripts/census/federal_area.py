"""
This script is intended to pull and ingest the U.S. national boundaries from
the census into a postgres database
"""
import zipfile
import shapefile
import requests
import os
import logging
from sqlalchemy.sql import func
import json

from scripts.database.database import upsert_dynamic, get_session
from ..logging_config import setup_logging
from ..database.models import Area

log = logging.getLogger(__name__)

US_SHAPEFILE_ZIP_URL = "https://www2.census.gov/geo/tiger/GENZ2023/shp/cb_2023_us_nation_5m.zip"
DATA_DIR = os.path.join(os.getcwd(), "_data", "federal_boundary")


def download_national_data():

    zip_filepath = os.path.join(DATA_DIR, "cb_2023_us_nation_5m.zip")

    response = requests.get(US_SHAPEFILE_ZIP_URL)

    response.raise_for_status()

    with open(zip_filepath, "wb") as f:
        f.write(response.content)

    with zipfile.ZipFile(zip_filepath, "r") as zip_ref:
        zip_ref.extractall(DATA_DIR)
        """
        This should include the following files:
        cb_2023_us_nation_5m.cpg
        cb_2023_us_nation_5m.dbf
        cb_2023_us_nation_5m.prj
        cb_2023_us_nation_5m.shp
        cb_2023_us_nation_5m.shp.ea.iso.xml
        cb_2023_us_nation_5m.shp.iso.xml
        cb_2023_us_nation_5m.shx
        """

    shapefile_path = os.path.join(DATA_DIR, "cb_2023_us_nation_5m.shp")
    sf = shapefile.Reader(shapefile_path)

    num_records = len(sf.records())

    log.info(f"Num records: {num_records}")

    record = sf.record(0)
    shape = sf.shape(0)

    return Area(
        id=f"ocd-division/country:us",
        classification="country",
        name="United States of America",
        abbrev="USA",
        fips_code=None,
        district_number=None,
        geo_id=record[1],
        geo_id_fq=record[0],
        legal_statistical_area_description_code=None,
        maf_tiger_feature_class_code=None,
        funcstat=None,
        land_area=None,
        water_area=None,
        centroid_lat=None,
        centroid_lon=None,
        geometry=func.ST_GeomFromGeoJSON(json.dumps(shape.__geo_interface__)),
    )



def main():
    # Setup
    with get_session() as session:
        os.makedirs(DATA_DIR, exist_ok=True)

        national_area = download_national_data()

        upsert_dynamic(session, national_area)

if __name__ == "__main__":
    setup_logging()
    main()