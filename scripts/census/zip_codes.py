import logging
import os
import zipfile
import json
import requests
import shapefile
import shutil
from sqlalchemy.sql import func, select

from ..database.models import Area, Person, PersonArea
from ..database.database import get_session, upsert_dynamic
from ..logging_config import setup_logging

log = logging.getLogger(__name__)

ZIP_CODE_URL = "https://www2.census.gov/geo/tiger/TIGER2024/ZCTA520/tl_2024_us_zcta520.zip"
DATA_DIR = os.path.join(os.getcwd(), "_data", "zip_codes")


def download_zip_codes():
    zip_filepath = os.path.join(DATA_DIR, "tl_2024_us_zcta520.zip")

    if not os.path.exists(zip_filepath):
        log.info("Downloading zip code data")

        # Zip file is kinda big (500mb)
        with requests.get(ZIP_CODE_URL, stream=True) as response:
            response.raise_for_status()
            with open(zip_filepath, 'wb') as file_out:
                for chunk in response.iter_content(chunk_size=1024 * 1024 * 16):
                    if chunk:
                        file_out.write(chunk)

        with zipfile.ZipFile(zip_filepath, "r") as zip_ref:
            zip_ref.extractall(DATA_DIR)
            """
            This should include the following files:
            tl_2024_us_zcta520.cpg
            tl_2024_us_zcta520.dbf
            tl_2024_us_zcta520.prj
            tl_2024_us_zcta520.shp
            tl_2024_us_zcta520.shp.ea.iso.xml
            tl_2024_us_zcta520.shp.iso.xml
            tl_2024_us_zcta520.shx
            """

    shapefile_path = os.path.join(DATA_DIR, "tl_2024_us_zcta520.shp")

    sf = shapefile.Reader(shapefile_path)

    num_records = len(sf.records())

    log.info(f"Num records: {num_records}")

    for i in range(num_records):
        record = sf.record(i)
        shape = sf.shape(i)

        zip_code = record[0]

        if i % 100 == 0:
            log.info(f"Finished {i} zip codes")

        ocd_id = f"ocd-division/country:us/zipcode:{zip_code}"
        yield Area(
            id=ocd_id,
            classification="zipcode",
            name=f"Zip Code {zip_code}",
            abbrev=zip_code,
            fips_code=None,
            district_number=None,
            geo_id=record[1],
            geo_id_fq=record[1],
            legal_statistical_area_description_code=None,
            maf_tiger_feature_class_code=record[4],
            funcstat=record[5],
            land_area=record[6],
            water_area=record[7],
            centroid_lat=float(record[8]),
            centroid_lon=float(record[9]),
            geometry=func.ST_GeomFromGeoJSON(json.dumps(shape.__geo_interface__)),
        )

def cleanup():
    shutil.rmtree(DATA_DIR)

def main():
    log.info("Ingesting zip codes")

    # Setup
    session = get_session()
    os.makedirs(DATA_DIR, exist_ok=True)

    for area in download_zip_codes():
        upsert_dynamic(session, area)

    # cleanup()

    # connect_zip_codes(session)

if __name__ == "__main__":
    setup_logging()
    main()