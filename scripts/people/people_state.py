"""
This script is intended to pull and ingest the state house and senate legislators for each state into a postgres database
"""


import yaml
import logging
import os
import shutil

from .people_utils import clone_repository, find_current_role
from ..database.database import get_session, upsert_dynamic
from ..database.models import Person
from ..logging_config import setup_logging
from ..utils import convert_area_id
from ..reference_data_helper import get_state_district_mapping

log = logging.getLogger(__name__)

REPO_URL = "https://github.com/openstates/people"
REPO_DIR = os.path.join(os.getcwd(), "_data", "people")

district_mapping = get_state_district_mapping()

# Definitely some stuff that we can't process yet, but very interesting nonetheless
def is_special_case(state_abbrev, person_data, current_role):

    # Maine has non-voting state house representatives that come from
    # the local Indian Reservations
    if state_abbrev == "me" and current_role["district"] in ["Passamaquoddy Tribe"]:
        return True

    return False


def map_role_type(state_abbrev, role_type):

    if state_abbrev == "dc":
        return "City Council"

    mapping = {
        "upper": "Senate",
        "lower": "House",
        "legislature": "Legislature"
    }

    return mapping[role_type.lower()]


def find_current_constituent_area_id(state_abbrev, current_role):
    """
    {
     "start_date" : "2023-01-03",
     "end_date" : "2025-01-03",
     "type" : "lower",
     "jurisdiction" : "ocd-jurisdiction/country:us/state:pa/government",
     "district" : "10"
    }
    """

    if state_abbrev == "ma":

        state_district_mapping = district_mapping[state_abbrev]
        # Mass has human-named districts versus numbers so we need a mapping to find the ID
        chamber = current_role["type"]

        if current_role['district'] in state_district_mapping[chamber]:
            return state_district_mapping[chamber][current_role['district']]
        elif current_role['district'] in state_district_mapping["special"]:
            return state_district_mapping["special"][current_role['district']]
        else:
            log.warning(f"District {current_role['district']} not found!")
            raise RuntimeError(f"Missing Massachusetts district! current_role: {current_role}")


    # DC is a bit weird
    if state_abbrev == "dc":
        # If the council member is "At-Large" - then their constituent area is all of DC
        if current_role["district"] in ["At-Large", "Chairman"]:
            return f"ocd-division/country:us/district:dc"
        # If the council member is not at large, then they represent a specific "Ward" or district
        ward_number = current_role["district"].replace("Ward ", "")
        return f"ocd-division/country:us/district:dc/ward:{ward_number}"

    # Nebraska is unicameral
    if state_abbrev == "ne" and current_role["type"] == "legislature":
        return f"ocd-division/country:us/state:{state_abbrev}/sldu:{current_role['district'].lower()}"

    # Idaho adds non-consequential letters to the district number for some reason
    if state_abbrev == "id" and current_role["type"] == "lower":
        district_number = ''.join(filter(str.isdigit, str(current_role["district"])))
        return f"ocd-division/country:us/state:{state_abbrev}/sldl:{district_number}"

    if current_role["type"] == "upper":
        return f"ocd-division/country:us/state:{state_abbrev}/sldu:{str(current_role['district']).lower()}"

    if current_role["type"] == "lower":
        return f"ocd-division/country:us/state:{state_abbrev}/sldl:{str(current_role['district']).lower()}"

    raise RuntimeError(f"Unknown role type: {current_role['type']}")


def parse_people_data(repo_dir):

    # Data is organized into directories keyed by 2 letter state abbrev

    data_dir = os.path.join(repo_dir, "data")

    for state_abbreviation in os.listdir(data_dir):
        state_directory_path = os.path.join(data_dir, state_abbreviation)

        """
        Some work:
        VT - requires district name mapping table <> Area ID "Essex Caledonia" -> "e-c" 
        MA - requires district name mapping table <> Area ID "3rd Bristol" -> "12"
        NH - requires district name mapping table <> Area ID "Rockingham 29" -> "729"
        
        Lots of work:
        PR - Need area mappings for Puerto Rico
        ND - North dakota house district mappings are out of date from the census tiger shapefiles - they were updated in 2023 versus the census in 2020. Some interesting options here, but for now going to skip ND
        """
        if state_abbreviation in ["vt", "nh", "pr", "nd"]:
            continue

        # US - Handled in the federal people script - this script is for states
        if state_abbreviation == "us":
            continue

        log.info(f"Processing state {state_abbreviation}")

        legislature_directory = os.path.join(state_directory_path, "legislature")

        for person_file in os.listdir(legislature_directory):
            log.info(f"Processing person file {person_file}")

            full_person_filepath = os.path.join(legislature_directory, person_file)

            with open(full_person_filepath, "r") as person_filehandle:
                person_data = yaml.safe_load(person_filehandle)

                current_role = find_current_role(person_data)

                constituent_area_id = find_current_constituent_area_id(state_abbreviation, current_role)

                # Some interesting cases here
                if is_special_case(state_abbreviation, person_data, current_role):
                    continue

                yield Person(
                    id=person_data["id"],
                    jurisdiction_area_id=convert_area_id(current_role['jurisdiction']),
                    constituent_area_id=constituent_area_id,
                    chamber=map_role_type(state_abbreviation, current_role["type"]),
                    name=person_data["name"],
                    first_name=person_data["given_name"],
                    last_name=person_data["family_name"],
                    other_names=[o["name"] for o in
                                 person_data["other_names"]] if "other_names" in person_data else None,
                    image=person_data["image"] if "image" in person_data else None,
                    email=person_data["email"] if "email" in person_data else None,
                    offices=person_data["offices"] if "offices" in person_data else None,
                    links=person_data["links"] if "links" in person_data else None,
                    ids=person_data["ids"] if "ids" in person_data else None,
                    sources=person_data["sources"] if "sources" in person_data else None,
                )


def cleanup(repo_dir):
    shutil.rmtree(repo_dir)


def main():

    # Setup
    with get_session() as session:
        os.makedirs(REPO_DIR, exist_ok=True)

        # Make sure we're pulling fresh data
        cleanup(REPO_DIR)

        # Data lives in a GH repository
        clone_repository(REPO_URL, REPO_DIR)

        for person in parse_people_data(REPO_DIR):
            upsert_dynamic(session, person)

        cleanup(REPO_DIR)


if __name__ == "__main__":
    setup_logging()
    main()