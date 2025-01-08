#!/usr/bin/env python3
# match_voters.py

import re
import json
import logging
import unicodedata
from ..database.models import Person
from thefuzz import process

log = logging.getLogger(__name__)


def get_vote_chamber(vote_event):
    # "organization": "~{\"classification\": \"upper\"}",
    try:
        return json.loads(vote_event["organization"][1:])['classification']
    except Exception:
        log.warning(f"Unexpected organization value: {vote_event['organization']}")
        return None


def get_state_from_area_id(area_id: str) -> str|None:
    """
    Extract the two-letter state code from an OCD division ID string.
    Examples:
      'ocd-division/country:us/state:co/cd:1' -> 'CO'
      'ocd-division/country:us/state:wi' -> 'WI'
    Returns None if not found.
    """
    match = re.search(r'(state|district):([a-z]{2})(?:\b|/)', area_id)
    if match:
        return match.group(2).upper()
    log.warning(f"Unable to find state from area id: {area_id}")
    return None


def get_state_from_name(voter_name: str) -> str|None:
    """
    Some voter names have the state (and party) injected like so:
    'Baldwin (D-WI)'
    'Jeffrey (TX)'
    """
    match = re.search(r'(.+) \(.?-?([A-Z]{2})\)', voter_name)
    if match:
        return match.group(2).upper()
    return None


def augment_persons_with_state(persons: list) -> list:
    """
    Adds a 'state' field to each person by parsing the 'constituent_area_id'.

    persons: [
      {
        'id': 'ocd-person/...',
        'constituent_area_id': 'ocd-division/country:us/state:co/cd:1',
        'last_name': 'Bennet',
        'first_name': 'Michael',
        'name': 'Michael F. Bennet',
        ...
      },
      ...
    ]

    After augmentation:
    [
      {
        'id': 'ocd-person/...',
        'constituent_area_id': 'ocd-division/country:us/state:co/cd:1',
        'last_name': 'Bennet',
        'first_name': 'Michael',
        'name': 'Michael F. Bennet',
        'state': 'CO'
      },
      ...
    ]
    """
    return_list = []
    for p in persons:
        p_dict = p._asdict()
        constituent_area_id = p_dict.get('constituent_area_id', '')
        p_dict['state'] = get_state_from_area_id(constituent_area_id)
        return_list.append(p_dict)
    return return_list


def remove_accents(input_str):
    return ''.join(
        c for c in unicodedata.normalize('NFD', input_str)
        if unicodedata.category(c) != 'Mn'
    )


def standardize_voter_name(voter_name: str) -> str:
    """
    Removes parentheses (party info, state info) from the voter_name
    and returns a simplified/cleaned version.
    Example:
      'Baldwin (D-WI)' -> 'Baldwin'
      'Bennet (D-CO)' -> 'Bennet'
    """
    return remove_accents(re.sub(r'\(.*?\)', '', voter_name).strip())


def _fuzzy_match_name(standardized_name: str, persons: list, threshold: int) -> str | None:
    """
    Internal helper to fuzzy match a standardized voter name among a list
    of Person objects. Returns the matched Person's id or None.

    :param standardized_name: e.g. 'Baldwin', 'Cruz', 'Case'
    :param persons: a filtered list of persons to match against,
                    each person dict can have 'id', 'name', 'first_name', 'last_name'
    :param threshold: integer fuzzy match threshold
    """

    if not persons:
        return None

    standardized_lower = standardized_name.lower()

    # Check for exact name match first (case insensitive)

    # 1) Check for exact name match (case-insensitive).
    #    If found, immediately return that person's ID.
    for p in persons:
        # If we find exact name match - just return
        if "name" in p and p["name"] and p["name"].lower() == standardized_lower:
            log.info(f"Matched {standardized_name} to {p['name']}")
            return p['id']

        # This is a little spooky - for Federal votes, they often only include the last name
        # but it's kinda questionable for me to do this...
        if "last_name" in p and p["last_name"] and p["last_name"].lower() == standardized_lower:
            log.info(f"Matched {standardized_name} to {p['last_name']}")
            return p["id"]

    # 2) Build a mapping from possible name variations to person ID.
    #    This allows us to fuzzy-match across first+last or full name.
    name_map = {}
    for p in persons:
        pid = p["id"]
        first = p.get("first_name") or ""
        last = p.get("last_name") or ""

        # a) first_name + last_name
        if first or last:
            composite = f"{first} {last}".strip()
            if composite:  # e.g. "Case" "Smith"
                name_map[composite] = pid

        # c) If you still want to consider p["name"] as is
        if p.get("name"):
            name_map[p["name"]] = pid

    # 3) Perform fuzzy matching on all name variations.
    if not name_map:
        return None

    possible_names = list(name_map.keys())
    match_result = process.extractOne(standardized_name, possible_names)
    if not match_result:
        return None

    best_name, best_score = match_result
    if best_score >= threshold:
        log.info(f"Matched {standardized_name} to {best_name}")
        return name_map[best_name]

    return None


def match_voter_to_person(
        voter_name: str,
        voter_state: str,
        vote_chamber: str,
        persons: list,
        threshold: int = 80
) -> str:
    """
    Fuzzy-match `voter_name` to the 'name' field of persons. Attempt
    to limit to persons whose 'state' matches voter_state, if present.

    Returns the 'id' of the best-matching person if above threshold,
    or None if no good match is found.

    :param voter_name: e.g., 'Baldwin (D-WI)'
    :param voter_state: e.g., 'WI' (parsed from jurisdiction_id)
    :param voter_chamber: e.g. 'lower' (which we need to map to House/Senate)
    :param persons: List of person dicts, each with keys including 'name' and 'state'.
    :param threshold: The fuzzy-match score threshold to accept a match (default 80).
    """
    # Standardize the name for better fuzzy matching
    standardized_voter = standardize_voter_name(voter_name)

    # First try fuzzy matching among persons in this state
    if voter_state:
        persons = filter(lambda p: p["state"] == voter_state, persons)

    # Some states use different mappings like "legislature" -> "City Council" which can be difficult
    if vote_chamber in ["lower", "upper"]:
        person_chamber = {
            "lower": "House",
            "upper": "Senate"
        }[vote_chamber]
        persons = filter(lambda p: p["chamber"] == person_chamber, persons)

    # easier for debugging
    persons = list(persons)

    # If no match found (or voter_state is None), fall back to ALL persons
    return _fuzzy_match_name(standardized_voter, persons, threshold)


def replace_voter_ids(votes: list, persons: list, vote_chamber: str, threshold: int = 80) -> list:
    """
    For each vote in votes, parse out the state from vote['jurisdiction_id'],
    then fuzzy match voter_name to Person data restricted by that state.
    If a match is found (score >= threshold), replace vote['voter_id']
    with the Person's 'id'.

    NOTE: Assumes that people objects have the state field set!

    votes: [
      {
        "option": "yes",
        "voter_name": "Baldwin (D-WI)",
        "voter_id": "~{\"name\": \"Baldwin (D-WI)\"}",
        "jurisdiction_id": "ocd-division/country:us/state:wi"
      },
      ...
    ]

    persons: [
      {
        "id": "ocd-person/...",
        "constituent_area_id": "ocd-division/country:us/state:wi",
        "last_name": "Baldwin",
        "first_name": "Tammy",
        "name": "Tammy Baldwin",
        "state": "WI"
      },
      ...
    ]

    :param threshold: The fuzzy match threshold to accept a match.
    :return: The modified list of votes with updated 'voter_id'.
    """
    updated_votes = []
    for vote in votes:
        voter_name = vote.get('voter_name', '')

        # Try to extract the state code from the vote
        voter_state = get_state_from_name(voter_name)

        matched_id = match_voter_to_person(
            voter_name=voter_name,
            voter_state=voter_state,
            vote_chamber=vote_chamber,
            persons=persons,
            threshold=threshold
        )
        if matched_id:
            vote['voter_id'] = matched_id
        else:
            log.warning(f"No Person row found for voter {voter_name}")

        updated_votes.append(vote)

    return updated_votes


def main():
    """
    Example usage of the above functions, showing how to:
    1) Augment persons with a 'state' field.
    2) Replace voter IDs in the votes data using fuzzy matching + state filter.
    3) Print the results.
    """
    # Sample persons data
    persons = [
        Person(id='ocd-person/d7c97bc3-b7cb-585b-b9e3-def97fcb9db6', constituent_area_id='ocd-division/country:us/state:wi', last_name='Baldwin', first_name='Tammy', name='Tammy Baldwin'),
        Person(id='ocd-person/80f88c07-5f6d-5ca3-8121-9202259a50f2', constituent_area_id='ocd-division/country:us/state:wy/cd:4', last_name='Barrasso', first_name='John', name='John Barrasso'),
        Person(id='ocd-person/16a0a125-6ebe-58b3-810f-df10c0e7df1f', constituent_area_id='ocd-division/country:us/state:co', last_name='Bennet', first_name='Michael', name='Michael F. Bennet'),
    ]


    # Add a 'state' field to each person
    persons = augment_persons_with_state(persons)

    # Sample votes data
    votes = [
        {
            "option": "yes",
            "voter_name": "Baldwin (D-WI)",
            "voter_id": "~{\"name\": \"Baldwin (D-WI)\"}",
            "jurisdiction_id": "ocd-division/country:us/state:wi"
        },
        {
            "option": "yes",
            "voter_name": "Barrasso (R-WY)",
            "voter_id": "~{\"name\": \"Barrasso (R-WY)\"}",
            "jurisdiction_id": "ocd-division/country:us/state:wy"
        },
        {
            "option": "yes",
            "voter_name": "Bennet (D-CO)",
            "voter_id": "~{\"name\": \"Bennet (D-CO)\"}",
            "jurisdiction_id": "ocd-division/country:us/state:co"
        },
    ]

    # Replace voter_ids using fuzzy matching + state filtering
    updated_votes = replace_voter_ids(votes, persons, vote_chamber="upper", voter_state=None, threshold=80)

    # Print out the updated votes
    print("=== Updated Votes ===")
    for vote in updated_votes:
        print(vote)


if __name__ == '__main__':
    main()
