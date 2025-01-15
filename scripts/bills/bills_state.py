import os
import logging
import argparse
import json
from sqlmodel import select
from datetime import datetime, timezone
from uuid import uuid5, NAMESPACE_OID

from ..database.database import upsert_dynamic, get_session
from ..database.models import Bill, VoteEvent, Person
from ..logging_config import setup_logging
from ..utils import convert_area_id
from .vote_matching import augment_persons_with_state, replace_voter_ids, get_vote_chamber

log = logging.getLogger(__name__)


def get_files_by_prefix(prefix: str, directory: str):
    return [os.path.join(directory, x) for x in os.listdir(directory) if x.startswith(prefix)]


def create_vote_event_id(vote_event_identifier):
    uuid_value = uuid5(NAMESPACE_OID, vote_event_identifier)
    return f"ocd-vote-event/{uuid_value}"


def create_bill_id(canonical_id, jurisdiction_area_id):
    uuid_value = uuid5(
        NAMESPACE_OID,
        "_".join([canonical_id, jurisdiction_area_id])
    )
    return f"ocd-bill/{uuid_value}"


def parse_date_str(date_str):
    if not date_str:
        return None

    formats = [
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%d"
    ]

    for format in formats:
        try:
            attempt = datetime.strptime(date_str, format)
            return attempt
        except ValueError:
            continue

    raise RuntimeError(f"Could not parse date '{date_str}'")

def main():
    log.info("Ingesting bills ")

    with get_session() as session:
        parser = argparse.ArgumentParser(description="Ingest bills")

        # Add arguments
        parser.add_argument("bill_data_directory_path", type=str, help="Path to directory containing bill data")

        # Parse the arguments
        args = parser.parse_args()

        bill_data_directory_path = args.bill_data_directory_path
        log.info(f"Bill data directory path: {bill_data_directory_path}")

        """
        There are 3 types of json files that we'll need in the directory
        1. Jurisdiction.json file - information about the jurisdiction relevant for the bills
        2. Bill.json files - information about each bill
        4. VoteEvent.json files - information about votes related to bills
    
        There are also organization.json files and event.json files that we are not ingesting 
        at this time.
        """

        # First identify the jurisdiction information for the federal bill data
        jurisdiction_filepaths = get_files_by_prefix("jurisdiction", bill_data_directory_path)
        if len(jurisdiction_filepaths) != 1:
            raise RuntimeError(f"Found {len(jurisdiction_filepaths)} jurisdiction files. Should be 1.")
        log.info(f"Jurisdiction file path: {jurisdiction_filepaths[0]}")
        with open(jurisdiction_filepaths[0]) as jurisdiction_file:
            jurisdiction_data = json.load(jurisdiction_file)
        jurisdiction_area_id = convert_area_id(jurisdiction_data["id"])

        bill_files = get_files_by_prefix("bill", bill_data_directory_path)

        bill_ids = []
        # Ingest bills
        for bill_filepath in bill_files:
            with open(bill_filepath) as bill_file:
                bill_data = json.load(bill_file)
                log.info(f"Handling bill file: {bill_filepath}")

                if bill_data["subject"]:
                    log.info(f"Subject: {bill_data['subject']}")
                    raise RuntimeError(json.dumps(bill_data, indent=2))

                if bill_data["actions"] and len(bill_data["actions"]) > 0:
                    latest_action = max(bill_data["actions"], key=lambda x: x["date"])
                    first_action = min(bill_data["actions"], key=lambda x: x["date"])
                else:
                    latest_action = None
                    first_action = None

                bill = Bill(
                    id=create_bill_id(bill_data["identifier"], jurisdiction_area_id),
                    title=bill_data["title"],
                    canonical_id=bill_data["identifier"],
                    jurisdiction_area_id=jurisdiction_area_id,
                    jurisdiction_level="state",
                    legislative_session=bill_data["legislative_session"],
                    from_organization=json.loads(bill_data["from_organization"][1:]),
                    classification=bill_data["classification"],
                    subject=bill_data["subject"],
                    abstracts=bill_data["abstracts"],
                    other_titles=bill_data["other_titles"],
                    other_identifiers=bill_data["other_identifiers"],
                    actions=bill_data["actions"],
                    sponsorships=bill_data["sponsorships"],
                    related_bills=bill_data["related_bills"],
                    versions=bill_data["versions"],
                    documents=bill_data["documents"],
                    citations=bill_data["citations"],
                    sources=bill_data["sources"],
                    extras=bill_data["extras"],
                    latest_action_date=parse_date_str(latest_action["date"] if latest_action else None),
                    first_action_date=parse_date_str(first_action["date"] if first_action else None),
                    updated_at=datetime.now(timezone.utc)
                )

                upsert_dynamic(session, bill)

                bill_ids.append(bill_data["identifier"])

        # Need to find the person ids for each vote which unfortunately is by name
        # Keeping just the name info to reduce memory pressure here but we'll need to
        # hold all of it. At least we can filter by jurisdiction area.
        people_data = session.exec(
            select(
                Person.id,
                Person.name,
                Person.first_name,
                Person.last_name,
                Person.constituent_area_id,
                Person.chamber
            ).where(
                Person.jurisdiction_area_id == jurisdiction_area_id
            )
        ).all()
        people_data = augment_persons_with_state(people_data)

        # Ingest votes
        vote_event_files = get_files_by_prefix("vote_event", bill_data_directory_path)
        for vote_event_filepath in vote_event_files:
            log.info(f"Handling vote file: {vote_event_filepath}")
            with open(vote_event_filepath) as vote_event_file:
                vote_event_data = json.load(vote_event_file)

                vote_bill_data_identifier = vote_event_data["bill_identifier"]
                if vote_bill_data_identifier in bill_ids:
                    vote_event_data['votes'] = replace_voter_ids(
                        vote_event_data['votes'],
                        people_data,
                        get_vote_chamber(vote_event_data))
                    bill_id = create_bill_id(vote_bill_data_identifier, jurisdiction_area_id)
                    vote_event = VoteEvent(
                        id=create_vote_event_id(vote_event_data["identifier"]),
                        bill_id=bill_id,
                        identifier=vote_event_data["identifier"],
                        motion_text=vote_event_data["motion_text"],
                        motion_classification=vote_event_data["motion_classification"],
                        # 2024-05-23T18:02:00+00:00
                        start_date=datetime.strptime(vote_event_data["start_date"], "%Y-%m-%dT%H:%M:%S%z"),
                        result=vote_event_data["result"],
                        chamber=json.loads(vote_event_data["organization"][1:])["classification"],
                        legislative_session=vote_event_data["legislative_session"],
                        votes=vote_event_data["votes"],
                        counts=vote_event_data["counts"],
                        sources=vote_event_data["sources"],
                        extras=vote_event_data["extras"]
                    )

                    upsert_dynamic(session, vote_event)
                    log.info(f"Upserted vote: {vote_event_filepath} for bill {bill_id}")
                else:
                    log.warning(
                        f"No bill found for vote event {vote_event_filepath} - Bill ID: {vote_bill_data_identifier}")


if __name__ == "__main__":
    setup_logging()
    main()