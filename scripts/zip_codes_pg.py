import shapefile
import logging
from dotenv import load_dotenv
import os
from pathlib import Path
from shapely.geometry import Polygon, shape
from shapely.wkt import dumps as wkt_dumps
import psycopg2
import urllib.parse

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[logging.StreamHandler()]
)

log = logging.getLogger(__name__)

parent_dir = Path(__file__).resolve().parent
env_path = parent_dir / '.env'
log.info(f"Loading .env from {env_path}")
load_dotenv(dotenv_path=env_path)

POSTGRES_DB_PASSWORD = os.getenv("POSTGRES_DB_PASSWORD")

# Connect to PostgreSQL
def connect_to_postgres():
    try:
        conn = psycopg2.connect(
            dbname="repcheck",
            user="postgres",
            password=POSTGRES_DB_PASSWORD,
            host="localhost",  # Change if using a remote database
            port="5432"  # Default port for PostgreSQL
        )
        return conn
    except Exception as e:
        log.error(f"Error connecting to PostgreSQL: {e}")
        raise

# Insert data into the ZIPCODES table
def insert_zip_code(conn, zip_code, polygon_wkt):
    try:
        cursor = conn.cursor()
        insert_query = """
        INSERT INTO ZIPCODES (zip_code, geometry)
        VALUES (%s, ST_GeomFromText(%s, 4326))
        ON CONFLICT (zip_code) DO NOTHING;
        """
        cursor.execute(insert_query, (zip_code, polygon_wkt))
        conn.commit()
        log.info(f"Inserted ZIP code: {zip_code}")
    except Exception as e:
        conn.rollback()
        log.error(f"Error inserting ZIP code {zip_code}: {e}")

# Process shapefile data
def process_data(shape_file_path):
    log.info("Running main method")
    
    log.info(f"Loading shapefile: {shape_file_path}")
    # Open the shapefile using iterators for memory efficiency
    sf = shapefile.Reader(shape_file_path)

    # Get the number of records for progress tracking
    num_records = len(sf)

    log.info("Loaded shapefile - processing zip codes")
    
    # Establish PostgreSQL connection
    conn = connect_to_postgres()

    # Use an index-based iterator to avoid loading all shapes/records at once
    for i in range(num_records):
        record = sf.record(i)
        shp = sf.shape(i)

        zcta = record[0]  # Assuming ZCTA is the first field

        # If you only want to process one specific zip code for testing
        if zcta != "15232":
            continue

        log.info(f"Processing ZIP code: {zcta} ({i}/{num_records})")

        # Convert shapefile geometry to Shapely Polygon
        polygon = shape(shp.__geo_interface__)
        
        # Convert the Shapely Polygon to WKT (Well-Known Text) format
        polygon_wkt = wkt_dumps(polygon)

        # Insert the ZIP code and its polygon into the database
        insert_zip_code(conn, zcta, polygon_wkt)
    
    # Close PostgreSQL connection
    conn.close()

if __name__ == "__main__":
    process_data("/mnt/volume_nyc1_01/raw_data/census/zip_codes/tl_2020_us_zcta520.shp")
