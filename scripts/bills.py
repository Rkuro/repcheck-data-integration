from sqlalchemy import create_engine, Column, Integer, String, JSON, DateTime, ForeignKey, Table
from sqlalchemy.orm import sessionmaker, relationship, declarative_base
from sqlalchemy.dialects.postgresql import JSONB, insert
import json
from .database.models import Bill, Zipcode, Person, ZipcodePeopleJoinTable, Jurisdiction
from .database.database import get_engine
from .plural_openstates.api.jurisdictions import get_jurisdiction
from .plural_openstates.api.bills import get_bills
import logging
import traceback
from datetime import datetime, timezone
from typing import Dict


# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[logging.StreamHandler()]
)


log = logging.getLogger(__name__)


PLURAL_DATESTR_FORMAT = '%Y-%m-%dT%H:%M:%S.%f%z'
DEFAULT_CUTOFF_DATE = datetime.strptime("2024-10-20", "%Y-%m-%d")

def upsert_bill(session, bill_data: Dict):
    log.info(f"Upserting bill data: {bill_data['title']}")

    # Replace empty strings with None for nullable fields
    for key, value in bill_data.items():
        if isinstance(value, str) and value.strip() == "" and key != "id":
            bill_data[key] = None
        else:
            bill_data[key] = value
        
    stmt = insert(Bill).values(**bill_data)
    
    stmt = stmt.on_conflict_do_update(
        index_elements=['id'],
        set_={key: stmt.excluded[key] for key in bill_data}
    )

    session.execute(stmt)


def update_bills(session, jurisdiction: Jurisdiction):
    log.info(f"Fetching bills for jurisdiction: {jurisdiction.id}")
    cutoff_date = jurisdiction.last_processed if jurisdiction.last_processed else DEFAULT_CUTOFF_DATE
    cutoff_date = cutoff_date.replace(tzinfo=timezone.utc)

    page = 1
    while True:
        log.info(f"Page: {page}")
        bills_json = get_bills(jurisdiction_id=jurisdiction.id, page=page)

        """
            "results" [...],
            "pagination": {
                "per_page": 52,
                "page": 1,
                "max_page": 1,
                "total_items": 3
            }
        """

        num_bills = len(bills_json["results"])
        for index, bill_json in enumerate(bills_json["results"]):
            log.info(f"Handling bill {index} of {num_bills}")
            bill_updated_at = datetime.strptime(bill_json["updated_at"], PLURAL_DATESTR_FORMAT)
            
            # If we hit a bill that was last updated further than our cutoff date then exit. We may want to revisit this
            if bill_updated_at < cutoff_date:
                log.info("Hit our exit criteria - bill too old for processing.")
                return
            
            upsert_bill(session, bill_json)

            # Just test a single bill
            return
        
        log.info(f"Upserted num bills: {num_bills}")
            
        # Go to the next page of results
        page += 1


        # If we hit the end of the universe then exit
        if page > bills_json["pagination"]["max_page"]:
            return
            
        

def add_jurisdiction(session, jurisdiction_upstream):
    log.info(f"Encountered new jurisdiction: {jurisdiction_upstream['id']}")
    jurisdiction_db = Jurisdiction(
        **{
            **jurisdiction_upstream,
            "last_processed": None
        }
    )
    session.add(jurisdiction_db)
    return jurisdiction_db


def process_jurisdiction(session, jurisdiction_id):
    log.info(f"Processing jurisdiction: {jurisdiction_id}")
    
    # First fetch the information about if/when we have last processed this
    # transaction

    db_entry = session.query(Jurisdiction).filter(Jurisdiction.id==jurisdiction_id).first()

    jurisdiction_upstream = get_jurisdiction(jurisdiction_id)

    # If we have never processed this jurisdiction, then add a new entry
    if not db_entry:
        db_entry = add_jurisdiction(session, jurisdiction_upstream)
        
    # Now we need to check if we need to fetch bills
    log.info(f"Encountered known jurisdiction: {jurisdiction_id}")

    latest_run_dt = datetime.strptime(jurisdiction_upstream["latest_runs"][-1]["end_time"], PLURAL_DATESTR_FORMAT)
    latest_run_dt = latest_run_dt.replace(tzinfo=timezone.utc)

    last_processed_dt = db_entry.last_processed
    last_processed_dt = last_processed_dt.replace(tzinfo=timezone.utc)
    log.info(f"Latest upstream run: {latest_run_dt}")
    log.info(f"Last Processed: {last_processed_dt}")

    if not last_processed_dt or latest_run_dt > last_processed_dt:
        # means we need to fetch new bills and updates!
        log.info("This jurisdiction has new updates that we need to fetch.")
        update_bills(session, jurisdiction=db_entry)
        
    else:
        # means we've processed since the last time this was updated and we
        # can just skip!
        log.info("We have already processed this jurisdiction since it was last updated. Skipping.")
        
    db_entry.last_processed = datetime.now(timezone.utc)


def main():
    
    try:
        # Create engine and session
        engine = get_engine()
        Session = sessionmaker(bind=engine)
        session = Session()
        # Step 1: Get iterator for zip_codes
        zip_codes = session.query(Zipcode).all()

        processed_jurisdictions = set()

        for zip_code_obj in zip_codes:
            zip_code = zip_code_obj.zip_code
            log.info(f"Processing zip code: {zip_code}")

            # Step 2: Get people for each zip code
            people: ZipcodePeopleJoinTable = zip_code_obj.zipcode_people

            for people_obj in people:
                person: Person = people_obj.person
                jurisdiction_id = person.jurisdiction_id

                if jurisdiction_id in processed_jurisdictions:
                    log.info(f"Skipping already processed jurisdiction: {jurisdiction_id}")
                    continue
                log.info(f"Handling person {person.name} with jurisdiction {jurisdiction_id}")

                # Step 2: Update bills for a given jurisdiction
                process_jurisdiction(session, jurisdiction_id)

                processed_jurisdictions.add(jurisdiction_id)
                break
            break

        # Commit changes
        session.commit()

    except Exception as e:
        log.error(e)
        log.error(traceback.format_exc())
    finally:
        session.close()

    log.info("Finished")

if __name__ == "__main__":
    main()
