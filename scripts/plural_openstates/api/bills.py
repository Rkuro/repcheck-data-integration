import requests
import time
from ..config import (
    PLURAL_HOST,
    PLURAL_API_KEY
)
import logging

log = logging.getLogger(__name__)

def get_bills(jurisdiction_id, page=1):
    
    params = {
        "include": [
            "sponsorships",
            "abstracts",
            "other_titles",
            "other_identifiers",
            "actions",
            "sources",
            "documents",
            "versions",
            "votes",
            "related_bills"
        ],
        "jurisdiction": jurisdiction_id,
        "sort": "updated_desc",
        "per_page": 20,
        "page": page
    }
    headers = {
        "X-API-KEY": PLURAL_API_KEY
    }
    start = time.time()
    response = requests.get(
        f"{PLURAL_HOST}/bills",
        headers=headers,
        params=params
    )
    end = time.time()
    log.info(f"Bills request took {end-start} seconds")

    return response.json()