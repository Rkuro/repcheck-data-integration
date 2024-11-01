import csv
from sqlalchemy import create_engine, Column, String, Integer, Date, Text, ARRAY
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime
from pathlib import Path
from urllib import parse
import logging
from dotenv import load_dotenv
import json
from models import Person, Zipcode, ZipcodePeopleJoinTable
from database import get_engine
from .plural_openstates.api.people import get_person

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[logging.StreamHandler()]
)

log = logging.getLogger(__name__)

# Function to parse date strings into datetime.date objects
def parse_date(date_str):
    if date_str:
        try:
            return datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return None
    return None

# Function to map CSV row data to Person object
def map_row_to_person(row):
    links = row['links'].split(';') if row['links'] else []
    sources = row['sources'].split(';') if row['sources'] else []

    return Person(
        id=row['id'],
        name=row['name'],
        current_party=row['current_party'],
        current_district=row['current_district'],
        current_chamber=row['current_chamber'],
        given_name=row['given_name'],
        family_name=row['family_name'],
        gender=row['gender'],
        email=row['email'],
        biography=row['biography'],
        birth_date=parse_date(row['birth_date']),
        death_date=parse_date(row['death_date']),
        image=row['image'],
        links=links,
        sources=sources,
        capitol_address=row['capitol_address'],
        capitol_voice=row['capitol_voice'],
        capitol_fax=row['capitol_fax'],
        district_address=row['district_address'],
        district_voice=row['district_voice'],
        district_fax=row['district_fax'],
        twitter=row['twitter'],
        youtube=row['youtube'],
        instagram=row['instagram'],
        facebook=row['facebook'],
        wikidata=row['wikidata']
    )


def ingest_people_csv(path_to_csv):

    engine = get_engine()
    Session = sessionmaker(bind=engine)
    session = Session()

    log.info(f"Running import on {path_to_csv}")
    with open(path_to_csv, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        # Iterate over each row and map it to a Person object
        people = [map_row_to_person(row) for row in reader]

    print("Saving objects to session and committing")
    # Add all Person objects to the session and commit the transaction
    session.bulk_save_objects(people)
    session.commit()

    # Close the session
    session.close()

    print("Finished")


def add_jurisdiction(session: Session, person: Person):
    log.info(f"Person ID: {person.id}")
    log.info(f"Name: {person.name}")

    person_info = get_person(person.id)

    """
    jurisdiction": {
        "id": "ocd-jurisdiction/country:us/government",
        "name": "United States",
        "classification": "country"
    }
    """

    if "jurisdiction" not in person_info:
        person_str = json.dumps(person_info, indent=4)
        raise RuntimeError(f"Unable to get jurisdiction: {person_str}")
    
    jurisdiction_id = person_info["jurisdiction"]["id"]
    
    log.info(f"Found jurisdiction: {jurisdiction_id}")

    person.jurisdiction_id = jurisdiction_id
        

def add_jurisdictions_to_people_by_zipcode():
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    session = Session()
    
    cursor = session.query(Zipcode).all()

    for zipcode in cursor:
        log.info(f"Handling zip code {zipcode.zip_code}")
        zipcode_people_join = zipcode.zipcode_people
        for join_entry in zipcode_people_join:
            if not join_entry.person.jurisdiction_id:
                log.info("No jurisdiction found for person, adding it.")
                add_jurisdiction(session, join_entry.person)
    log.info("Committing")
    session.commit()
    session.close()
    log.info("Finished")


if __name__ == "__main__":
    # ingest_people_csv("/mnt/volume_nyc1_01/raw_data/plural/people/us.csv")

    add_jurisdictions_to_people_by_zipcode()