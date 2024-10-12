import shapefile
import requests
import zipfile
import os
import json
import logging
from shapely.geometry import Polygon
from plural_openstates.config import PLURAL_API_KEY, PLURAL_HOST
from plural_openstates.people import Reps, get_representatives_for_lat_lon
import gc

logging.basicConfig(
    level=logging.INFO,  
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
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

# Function to query representatives by lat/lon
def query_representatives(lat, lon):
    return get_representatives_for_lat_lon(lat, lon)

# Function to simplify polygon for large polygons
def simplify_polygon(points, tolerance=5.0):
    polygon = Polygon(points)
    simplified_polygon = polygon.simplify(tolerance, preserve_topology=True)
    return simplified_polygon.exterior.coords

# Retrieve representatives for lat/lon
def get_lat_lon_reps(lat, lon):
    return set(rep["id"] for rep in query_representatives(lat, lon))

def serialize_sets(obj):
    if isinstance(obj, set):
        return list(obj)
    return obj

# Process data one shape and record at a time
def process_data(shape_file_path):
    log.info("Running main method")
    
    # Open the shapefile using iterators for memory efficiency
    sf = shapefile.Reader(shape_file_path)

    # Get the number of records for progress tracking
    num_records = len(sf)

    # Loop through each ZIP code and calculate the representatives
    zip_code_representatives = {}

    log.info("Loaded shapefile - processing zip codes")
    
    # Use an index-based iterator to avoid loading all shapes/records at once
    for i in range(num_records):
        record = sf.record(i)
        shape = sf.shape(i)

        zcta = record[0]  # Assuming ZCTA is the first field
        zip_code_representatives[zcta] = set()

        # Log progress periodically
        if i % 100 == 0:
            log.info(f"Processing zip code: {zcta} ({i}/{num_records})")

        try:
            points = shape.points  # Get raw points from the shape
            polygon = Polygon(points)
            centroid = polygon.centroid

            # First - get the reps for the centroid of the ZIP code
            centroid_reps = get_lat_lon_reps(centroid.y, centroid.x)
            zip_code_representatives[zcta].update(centroid_reps)

            # Check for boundary differences
            corner_points = [(y, x) for x,y in get_bounding_box_points(shape)]
            is_cross_district_zip_code = False

            for lat, lon in corner_points:
                latlonreps = get_lat_lon_reps(lat, lon)
                if not centroid_reps.issuperset(latlonreps):
                    is_cross_district_zip_code = True
                    break
            
            # If cross-district, simplify polygon and query further
            if is_cross_district_zip_code:
                simplified_points = simplify_polygon(shape.points)
                for lon, lat in simplified_points:
                    latlonreps = get_lat_lon_reps(lat, lon)
                    zip_code_representatives[zcta].update(latlonreps)

        except Exception as e:
            log.error(f"Error processing ZIP code {zcta}: {e}")
        
        # Save partial results and free memory after every 1000 records
        if i % 1000 == 0:
            with open(f"output_part_{i}.json", "w") as output_f:
                json.dump(zip_code_representatives, output_f, default=serialize_sets)
            zip_code_representatives.clear()  # Clear memory
            gc.collect()  # Force garbage collection
    
    # Final output
    with open("output.json", "w") as output_f:
        json.dump(zip_code_representatives, output_f, default=serialize_sets)

# Function to download shapefile if not present
def check_data_downloaded(expected_path):
    return os.path.exists(expected_path)

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

# Main function
def main():
    expected_path = os.path.join(os.getcwd(), 'zip_codes', 'tl_2020_us_zcta520.shp')
    if not check_data_downloaded(expected_path):
        log.info("Data not downloaded - downloading...")
        download_data()
    else:
        log.info("Data already downloaded - processing")

    log.info("Processing data")
    process_data(expected_path)

# Run the main function
if __name__ == "__main__":
    main()
