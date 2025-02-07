import os
import logging
import requests
import gzip
from shapely.geometry import shape

from sqlalchemy.sql import func
import subprocess
import json
from uuid import uuid5, NAMESPACE_OID

from ..database.database import upsert_dynamic, get_session
from ..logging_config import setup_logging
from ..database.models import PrecinctElectionResultArea

log = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.getcwd(), "_data", "election_data")


def ungzip(filepath, output_filepath):
    # Open the .gz file and write its decompressed content to the output file
    with gzip.open(filepath, 'rb') as gz_file:
        with open(output_filepath, 'wb') as out_file:
            out_file.write(gz_file.read())

def download_nytimes_data():

    topojson_url = "https://int.nyt.com/newsgraphics/elections/map-data/2024/national/precincts-with-results.topojson.gz"
    csv_url = "https://int.nyt.com/newsgraphics/elections/map-data/2024/national/precincts-with-results.csv.gz"

    topo_json_response = requests.get(topojson_url)
    csv_response = requests.get(csv_url)

    # Ensure we can fetch
    topo_json_response.raise_for_status()
    csv_response.raise_for_status()

    topo_gzip_filepath = os.path.join(DATA_DIR, "precincts-with-results.topojson.gz")
    csv_gzip_filepath = os.path.join(DATA_DIR, "precincts-with-results.csv.gz")

    with open(topo_gzip_filepath, "wb") as topojson_file_raw:
        topojson_file_raw.write(topo_json_response.content)

    with open(csv_gzip_filepath, "wb") as csv_file_raw:
        csv_file_raw.write(csv_response.content)

    # Un-gzip
    topojson_filepath = os.path.join(DATA_DIR, "precincts-with-results.topojson")
    ungzip(topo_gzip_filepath, topojson_filepath)
    csv_filepath = os.path.join(DATA_DIR, "precincts-with-results.csv")
    ungzip(csv_gzip_filepath, csv_filepath)

    return topojson_filepath, csv_filepath


def ingest_geojson(geojson_lines_filepath):
    counter = 0
    with get_session() as session:
        with open(geojson_lines_filepath, "r") as geojson_file_raw:
            for line in geojson_file_raw:
                precinct_geojson = json.loads(line)

                props = precinct_geojson["properties"]

                # Convert GeoJSON to Shapely MultiPolygon
                multipolygon = shape(precinct_geojson["geometry"])

                # Compute the centroid
                centroid = multipolygon.centroid

                precinct = PrecinctElectionResultArea(
                    precinct_id=str(uuid5(NAMESPACE_OID, props["GEOID"])),
                    state=props["state"],
                    votes_dem=props["votes_dem"],
                    votes_rep=props["votes_rep"],
                    votes_total=props["votes_total"],
                    pct_dem_lead=props["pct_dem_lead"],
                    official_boundary=props["official_boundary"],
                    geometry=func.ST_GeomFromGeoJSON(json.dumps(precinct_geojson["geometry"])),
                    centroid_lat=centroid.y,
                    centroid_lon=centroid.x
                )


                upsert_dynamic(session, precinct)

                counter += 1
                if counter % 100 == 0:
                    log.info(f"Ingested {counter} precincts")

def main():
    os.makedirs(DATA_DIR, exist_ok=True)

    # log.info("Downloading precinct election data")
    # topojson_filepath, csv_filepath = download_nytimes_data()

    geojson_lines_filepath = os.path.join(DATA_DIR, "precincts-with-results.geojson")
    # # convert to geojson lines
    # # This runs a npm/node module as a cli, which is.. idk.. not great
    # # nytimes wanted to use topojson likely to reduce storage space usage
    # # but its kinda annoying cuz python tooling is not very mature for it
    # subprocess.run(
    #     ["topo2geo", "--newline-delimited", f"tiles={geojson_lines_filepath}", "-i", topojson_filepath]
    # )

    ingest_geojson(geojson_lines_filepath)


if __name__ == "__main__":
    setup_logging()
    main()