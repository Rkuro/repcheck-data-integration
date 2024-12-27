"""
This script is intended to pull and ingest the U.S. congressional legislators
(both house and senate) into a postgres database.
"""

import yaml
from typing import Tuple
import json
from datetime import datetime, timezone

from scripts.database.database import upsert_dynamic, get_session
from ..database.models import Person
import os
import shutil
import logging
from ..logging_config import setup_logging
from ..fips_helper import get_fips_state_mapping
from .people_utils import clone_repository

log = logging.getLogger(__name__)

REPO_URL = "https://github.com/openstates/people"
REPO_DIR = os.path.join(os.getcwd(), "_data", "people")

state_mapping = {v["name"]: v["abbreviation"] for k,v in get_fips_state_mapping().items()}
state_abbreviations = [v["abbreviation"] for _, v in get_fips_state_mapping().items()]


def is_special_case(current_role):
    if current_role["type"] == "upper" and current_role["district"] not in state_mapping:
        return True

    if current_role["type"] == "lower" and current_role['district'].split("-")[0] not in state_abbreviations:
        return True

    if current_role["type"] == "lower" and current_role["district"].split("-")[0] in ["AS", "PR", "GU", "VI"]:
        return True

    return False


def find_current_constitutent_area_id(current_role):
    """
    {
     "start_date" : "2023-01-03",
     "end_date" : "2025-01-03",
     "type" : "lower",
     "jurisdiction" : "ocd-jurisdiction/country:us",
     "district" : "TX-13"
    }
    """
    # If it is a senator, then their constituent area is the entire
    # state
    if current_role["type"] == "upper":
        # district is the full state name, e.g. 'Massachusetts'
        state_abbreviation = state_mapping[current_role["district"]]
        return f"ocd-division/country:us/state:{state_abbreviation.lower()}"

    # If it is a house rep, then we need to find their district
    # We assume it follows "ST-NN" format
    # Where ST is the state abbreviation and
    # NN is the district number
    if "-" not in current_role["district"]:
        raise RuntimeError(f"Unexpected district format {current_role['district']}")
    split = current_role["district"].split("-")
    state = split[0]
    district = split[1]

    # We are denoting at large districts as "at-large"
    if district == "AL":
        district = "at-large"

    # Cuz DC is not a state :sigh:
    if state == "DC":
        return f"ocd-division/country:us/district:{state.lower()}/cd:{district}"

    return f"ocd-division/country:us/state:{state.lower()}/cd:{district}"



def map_role_type(role_type):
    return {
        "upper": "Senate",
        "lower": "House"
    }[role_type]


def find_current_role(person_data):
    """
    [ {
          "start_date" : "2023-01-03",
          "end_date" : "2025-01-03",
          "type" : "lower",
          "jurisdiction" : "ocd-jurisdiction/country:us/government",
          "district" : "TX-13"
        }, ...
    ]
    """
    roles = person_data["roles"]
    required_keys = ["start_date", "type", "jurisdiction", "district"]
    for role in roles:
        if not all([key in role for key in required_keys]):
            raise RuntimeError(f"Unexpected role structure: {role}")

        start_date = role["start_date"]

        # Sometimes there's not an end date included yet (for newly elected folks)
        if "end_date" in role:
            end_date = role["end_date"]

            if start_date <= datetime.now(timezone.utc).date() <= end_date:
                return role
        else:
            if start_date < datetime.now(timezone.utc).date():
                return role

    log.warning(f"Unable to find current role for person: {person_data}")
    raise RuntimeError(f"Unable to find current role for person: {person_data}")


def parse_people_data(repo_dir):
    federal_people_directory = os.path.join(repo_dir, "data", "us", "legislature")

    for person_file in os.listdir(federal_people_directory):
        log.info(f"Parsing person file {person_file}...")

        full_person_filepath = os.path.join(federal_people_directory, person_file)

        with open(full_person_filepath, "r") as person_filehandle:
            person_data = yaml.safe_load(person_filehandle)

            current_role = find_current_role(person_data)

            log.info(f"Current role district: {current_role['district']}")

            constituent_area_id = find_current_constitutent_area_id(
                current_role
            )

            # We are not handling special cases such as american samoa, virgin islands, etc. at this time
            if is_special_case(current_role):
                continue

            yield Person(
                id=person_data["id"],
                jurisdiction_area_id="ocd-division/country:us",
                constituent_area_id=constituent_area_id,
                chamber=map_role_type(current_role["type"]),
                name=person_data["name"],
                first_name=person_data["given_name"],
                last_name=person_data["family_name"],
                other_names=[o["name"] for o in person_data["other_names"]],
                image=person_data["image"],
                email=person_data["email"],
                offices=person_data["offices"] if "offices" in person_data else None,
                links=person_data["links"] if "links" in person_data else None,
                ids=person_data["ids"] if "ids" in person_data else None,
                sources=person_data["sources"],
            )


def cleanup(repo_dir):
    shutil.rmtree(repo_dir)

def main():

    # Setup
    session = get_session()
    os.makedirs(REPO_DIR, exist_ok=True)

    # Data lives in a GH repository
    clone_repository(REPO_URL, REPO_DIR)

    for person in parse_people_data(REPO_DIR):
        upsert_dynamic(session, person)
    # cleanup(REPO_DIR)

if __name__ == "__main__":
    setup_logging()
    main()