import shapefile
import requests
import zipfile
import os
import json
import logging
from shapely.geometry import Polygon
from plural_openstates.config import PLURAL_API_KEY, PLURAL_HOST
from plural_openstates.people import Reps, get_representatives_for_lat_lon

"""
Creates a mapping of zip codes to legislators. Takes a LONG time to run due to zip
code to voting district overlaps and the plural API rate limits (10 per minute).

There are 33,791 zip codes total (downloaded from the 2020 US census).
"""


logging.basicConfig(
    level=logging.INFO,  # Set the minimum logging level
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',  # Log message format
    datefmt='%Y-%m-%d %H:%M:%S',  # Date format
    handlers=[
        logging.StreamHandler()
    ]
)

log = logging.getLogger(__name__)

# Function to get bounding box points
def get_bounding_box_points(polygon):
    lons, lats = zip(*polygon.points)
    min_lat, max_lat, min_lon, max_lon = min(lats), max(lats), min(lons), max(lons)
    return [(min_lon, min_lat), (min_lon, max_lat), (max_lon, min_lat), (max_lon, max_lat)]

# Function to query your representative service for a given lat/lon
def query_representatives(lat, lon):
    return get_representatives_for_lat_lon(lat, lon)

# Function to simplify polygon
def simplify_polygon(points, tolerance=5.0):
    polygon = Polygon(points)
    simplified_polygon = polygon.simplify(tolerance, preserve_topology=True)
    return simplified_polygon.exterior.coords


def get_lat_lon_reps(lat, lon):
    return set(rep["id"] for rep in query_representatives(lat, lon))


def are_there_new_reps(centroid_reps: Reps, latlonrep: Reps):
    return not (
        centroid_reps.get_senators().issuperset(latlonrep.get_senators()) and
        centroid_reps.get_reps().issuperset(latlonrep.get_reps()) and
        centroid_reps.get_state_senators().issuperset(latlonrep.get_state_senators()) and
        centroid_reps.get_state_reps().issuperset(latlonrep.get_state_reps())
    )

def serialize_sets(obj):
    if isinstance(obj, set):
        return list(obj)

    return obj

def process_data(shape_file_path):
    log.info("Processing zip codes")

    # Open the shapefile containing the ZIP code polygons
    sf = shapefile.Reader(shape_file_path)

    # Loop through each ZIP code and calculate the representatives
    zip_code_representatives = {}

    for record, shape in zip(sf.records(), sf.shapes()):
        zcta = record[0]  # Assuming ZCTA is the first field
        zip_code_representatives[zcta] = set()

        log.info(f"Processing zip code: {zcta}")

        # Get the centroid of the polygon
        polygon = Polygon(shape.points)
        centroid = polygon.centroid
        
        # First - get the reps for the centroid of the zip code
        # and the bounding box coordinates. If they differ then
        # We need to look more closely at the points as this zip
        # code may cross district boundaries. Note that we do not
        # want to add the corner points to the mapping as the corners
        # may not actually be part of the zip code itself.
        # Note lat/lon order!

        # Centroid first
        centroid_reps = get_lat_lon_reps(centroid.y, centroid.x)
        zip_code_representatives[zcta] = centroid_reps

        # Then corner points
        corner_points = [(y, x) for x,y in get_bounding_box_points(shape)]
        is_cross_district_zip_code = False
        for lat, lon in corner_points:
            latlonreps = get_lat_lon_reps(lat, lon)

            for rep_id in latlonreps:
                if rep_id not in centroid_reps:
                    is_cross_district_zip_code = True
        
        # If bounding box points return different results, sample more points
        if is_cross_district_zip_code:
            log.info(f"Found cross district zip code: {zcta}")
            # Simplify polygon and sample fewer points within to try and grab
            # all reps that might be represented by the zip code
            simplified_points = simplify_polygon(shape.points)
            for lon, lat in simplified_points:
                latlonreps = get_lat_lon_reps(lat, lon)

                zip_code_representatives[zcta].update(latlonreps)

        # Consolidate results into list for JSON
        zip_code_representatives[zcta] = list(zip_code_representatives[zcta])

    # Now you have a dictionary mapping ZIP codes to all unique representatives
    for zcta, reps in zip_code_representatives.items():
        log.info(f"ZCTA {zcta} has representatives: {reps}")

    with open("output.json", "w") as output_f:
        json.dump(zip_code_representatives, output_f, default=serialize_sets)


def check_data_downloaded(expected_path):
    
    if os.path.exists(expected_path):
        return True

    return False


def download_data():
    zip_file_name = "tl_2020_us_zcta520.zip"
    url = f"https://www2.census.gov/geo/tiger/TIGER2020/ZCTA520/{zip_file_name}"

    response = requests.get(url)

    output_directory = os.path.join(os.getcwd(), 'zip_codes')

    os.makedirs(output_directory, exist_ok=True)

    with open(os.path.join(output_directory, zip_file_name), 'wb') as output_f:
        output_f.write(response.content)

    with zipfile.ZipFile(os.path.join(output_directory, zip_file_name), 'r') as zip_ref:
        zip_ref.extractall(output_directory)


def cleanup():
    pass


def main():
    expected_path = os.path.join(os.getcwd(), 'zip_codes', 'tl_2020_us_zcta520.shp')
    if not check_data_downloaded(expected_path):
        log.info("Data not downloaded - downloading...")
        download_data()
    else:
        log.info("Data already downloaded - processing")

    log.info("Processing data")
    process_data(expected_path)


if __name__ == "__main__":
    main()