from git import Repo, GitCommandError
import logging
from datetime import datetime, timezone

log = logging.getLogger(__name__)


# Interestingly reusable for federal and state
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
    required_keys = ["type", "jurisdiction", "district"]

    # If it's the only role, then we assume its current
    if len(roles) == 1:
        return roles[0]

    # Some guesswork required here since the data can be chaotic
    potential_role = None
    for role in roles:

        # Not dealing with this now...
        if role["type"] in ["mayor"]:
            continue

        if not all([key in role for key in required_keys]):
            raise RuntimeError(f"Unexpected role structure: {role}")

        start_date = None
        end_date = None
        if "start_date" in role:
            start_date = role["start_date"]
            if isinstance(start_date, str):
                start_date = datetime.strptime(start_date, "%Y-%m-%d").date()

        if "end_date" in role:
            end_date = role["end_date"]
            if isinstance(end_date, str):
                end_date = datetime.strptime(end_date, "%Y-%m-%d").date()

        # There are 4 cases:

        # We have both start and end date
        if start_date and end_date:
            if start_date <= datetime.now(timezone.utc).date() <= end_date:
                return role
            else:
                continue

        # Means only start date
        if start_date:
            # If there is only a start date, I'm going to say it's a potential date
            # if no others take the cake
            potential_role = role
            continue

        # Means only end date
        if end_date:
            if end_date < datetime.now(timezone.utc).date():
                continue

            # If there is only an end date and its in the future, we're gonna guess
            # that this is the current role
            return role

        # Means neither - which is a potential one if the others are non-descript or
        # in the past
        potential_role = role

    if potential_role:
        # log.warning(f"Using best guess for current role {potential_role}")
        return potential_role

    log.warning(f"Unable to find current role for person: {person_data}")
    raise RuntimeError(f"Unable to find current role for person: {person_data}")


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