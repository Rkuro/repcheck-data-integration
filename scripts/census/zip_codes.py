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


def connect_zip_codes(session):
    # Zip codes are slightly odd in that since we are designing the UX
    # around them, we need to create some edges between them and other data:
    # Zip code -> Person (based on representative district area not jurisdiction)
    log.info("Connecting zip codes")
    people = session.exec(select(Person)).scalars().all()

    for person in people:
        log.info(f"Connecting person {person.name} to zip codes")
        constituent_area = session.exec(
            select(Area).where(Area.id == person.constituent_area_id)
        ).scalars().one_or_none()

        if not constituent_area:
            raise RuntimeError(f"No constituent area found for {person.name}")

        zip_code_areas = session.exec(
            select(Area).where(
                Area.classification == "zipcode",
                func.ST_Intersects(Area.geometry, constituent_area.geometry)
            )
        ).scalars().all()

        for zip_area in zip_code_areas:
            association = PersonArea(
                person_id=person.id,
                area_id=zip_area.id,
                relationship_type="constituent_area_zip_code"
            )
            session.add(association)

    session.commit()
    session.close()

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

    connect_zip_codes(session)

if __name__ == "__main__":
    setup_logging()
    main()