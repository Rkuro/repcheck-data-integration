import requests
import json

from .config import (
    PLURAL_HOST,
    PLURAL_API_KEY
)

"""
We will likely not need to update jurisdictions very often. These change with the
bicennial census (2010, 2020, etc) for Federal and State districts, and potentially
more often for local municipalities, but once a week should be more than often enough
for these.
"""

def process_jurisdictions():
    
    # While there are still pages
    while True:
        pass
    

def get_jurisdictions(page=1):
    params = {
        "include": ["organizations", "legislative_sessions", "latest_runs"]
    }
    headers = {
        "X-API-KEY": PLURAL_API_KEY
    }
    response = requests.get(
        f"{PLURAL_HOST}/jurisdictions",
        headers=headers,
        params=params
    )

    jurisdictions_page = response.json()

    """
        "results" [...],
        "pagination": {
            "per_page": 52,
            "page": 1,
            "max_page": 1,
            "total_items": 3
        }
    """

    return jurisdictions_page
    

def handle_jurisdictions_page(jurisdictions_page):
    pass

def handle_jurisdiction():
    pass