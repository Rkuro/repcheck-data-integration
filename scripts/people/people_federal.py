"""
This script is intended to pull and ingest the U.S. congressional legislators
(both house and senate) into a postgres database.
"""

import yaml
import json
from ..database.models import Person
from git import Repo, GitCommandError
import os
import shutil
import logging
from ..logging_config import setup_logging

log = logging.getLogger(__name__)

REPO_URL = "https://github.com/openstates/people"
REPO_DIR = os.path.join(os.getcwd(), "_data", "people")


def clone_repository(repo_url, clone_dir):
    """
    Clone a git repository to a specific directory.

    :param repo_url: The URL of the git repository to clone.
    :param clone_dir: The directory where the repository will be cloned.
    """
    try:
        print(f"Cloning repository from {repo_url} to {clone_dir}...")
        Repo.clone_from(repo_url, clone_dir)
        print("Repository cloned successfully.")
    except GitCommandError as e:
        if e.status == 128:
            log.info("Repo directory non-empty, assuming it already exists.")
            return
    except Exception as e:
        print(f"An error occurred: {e}")

def parse_people_data(repo_dir):
    federal_people_directory = os.path.join(repo_dir, "data", "us", "legislature")

    for person_file in os.listdir(federal_people_directory):
        log.info(f"Parsing person file {person_file}...")

        full_person_filepath = os.path.join(federal_people_directory, person_file)

        with open(full_person_filepath, "r") as person_filehandle:
            person_data = yaml.safe_load(person_filehandle)

            print(json.dumps(person_data, indent=4, default=str))

            raise RuntimeError("We haven't completed the jurisdiction data yet - need that first!")

def ingest_people_data(people_data):
    pass

def cleanup(repo_dir):
    shutil.rmtree(repo_dir)

def main():

    os.makedirs(REPO_DIR, exist_ok=True)

    clone_repository(REPO_URL, REPO_DIR)

    repo_data = parse_people_data(REPO_DIR)

    ingest_results = ingest_people_data(repo_data)

    # cleanup(REPO_DIR)

if __name__ == "__main__":
    setup_logging()
    main()