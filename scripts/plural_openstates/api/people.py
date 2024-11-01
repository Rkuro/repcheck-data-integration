import logging
import json
import requests
import time
from urllib import parse

from ..config import PLURAL_API_KEY, PLURAL_HOST

log = logging.getLogger(__name__)



def get_person(person_id: str):
    params = {
        "id": parse.quote(person_id)
    }
    headers = {
        "X-API-KEY": PLURAL_API_KEY
    }
    response = requests.get(
        f"{PLURAL_HOST}/people",
        headers=headers,
        params=params
    )

    result_dict = response.json()

    if "results" not in result_dict or len(result_dict["results"]) != 1:
        raise RuntimeError(f"Unexpected person result: {json.dumps(result_dict, indent=4)}")

    """
        "results" [...],
        "pagination": {
            "per_page": 52,
            "page": 1,
            "max_page": 1,
            "total_items": 3
        }
    """

    return result_dict["results"][0]

def send_people_geo_request(lat, lon):
    params = {
        "include": [],
        "lat": lat,
        "lng": lon
    }
    headers = {
        "X-API-KEY": PLURAL_API_KEY
    }
    response = requests.get(
        f"{PLURAL_HOST}/people.geo",
        headers=headers,
        params=params
    )

    return response.json()

def get_representatives_for_lat_lon(lat, lon):
    log.info(f"Getting representatives for lat: {lat}, lon:{lon}")
    while True:
        result_json = send_people_geo_request(lat, lon)
        
        if "detail" in result_json and "exceeded limit" in result_json["detail"]:
            # {
            #     "detail": "exceeded limit of 10/min: 11"
            # }
            log.info("Hit API limit of 10 requests per minute, waiting 65 seconds...")
            time.sleep(65)
        elif 'results' not in result_json:
            raise RuntimeError(f"Bad response from plural: {json.dumps(result_json, indent=4)}")
        else:
            return result_json["results"]



def is_federal_senator(person):
    return (
        person["jurisdiction"]["classification"] == "country" and
        person["current_role"]["title"] == "Senator"
    )


def is_federal_representative(person):
    return (
        person["jurisdiction"]["classification"] == "country" and
        person["current_role"]["title"] == "Representative"
    )

def is_state_senator(person):
    return (
        person["jurisdiction"]["classification"] == "state" and
        person["current_role"]["title"] == "Senator"
    )

def is_state_representative(person):
    return (
        person["jurisdiction"]["classification"] == "state" and
        person["current_role"]["title"] == "Representative"
    )


def check_set_inclusion(set_a, set_b):
    return set_a.issubset(set_b) or set_b.issubset(set_a)


class Reps:
    def __init__(self):
        self.people = {
            "federal": {
                "senators": set(),
                "reps": set()
            },
            "state": {
                "senators": set(),
                "reps": set()
            }
        }
    
    def get_senators(self):
        return self.people["federal"]["senators"]
    
    def add_senators(self, senators):
        self.people["federal"]["senators"].update(senators)

    def get_reps(self):
        return self.people["federal"]["reps"]

    def add_reps(self, reps):
        self.people["federal"]["reps"].update(reps)

    def get_state_senators(self):
        return self.people["state"]["senators"]
    
    def add_state_senators(self, state_senators):
        self.people["state"]["senators"].update(state_senators)

    def get_state_reps(self):
        return self.people["state"]["reps"]

    def add_state_reps(self, state_reps):
        self.people["state"]["reps"].update(state_reps)        

    def consolidate(self, other):
        self.add_senators(other.get_senators())
        self.add_reps(other.get_reps())
        self.add_state_senators(other.get_state_senators())
        self.add_state_reps(other.get_state_reps())

    def update(self, reps):
        for rep in reps:
            if is_federal_senator(rep):
                self.people["federal"]["senators"].add(rep["id"])
            elif is_federal_representative(rep):
                self.people["federal"]["reps"].add(rep["id"])
            elif is_state_senator(rep):
                self.people["state"]["senators"].add(rep["id"])
            elif is_state_representative(rep):
                self.people["state"]["reps"].add(rep["id"])
            else:
                rep_str = json.dumps(rep, indent=4)
                log.warning(f"Unable to determine the type of representative for this one: {rep_str}")

    def to_dict(self):
        return self.people