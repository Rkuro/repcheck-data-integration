import requests
import json
from plural_openstates.config import (
    PLURAL_API_KEY,
    PLURAL_HOST
)

"""
Method	Description	Interactive Docs
/jurisdictions	Get list of available jurisdictions.	try it!
/jurisdictions/{jurisdiction_id}	Get detailed metadata for a particular jurisdiction.	try it!
/people	List or search people (legislators, governors, etc.)	try it!
/people.geo	Get legislators for a given location.	try it!
/bills	Search bills by various criteria.	try it!
/bills/ocd-bill/{uuid}	Get bill by internal ID.	try it!
/bills/{jurisdiction}/{session}/{id}	Get bill by jurisdiction, session, and ID.	try it!
/committees	Get list of committees by jurisdiction.	try it!
/committees/{committee_id}	Get details on committee by internal ID.	try it!
/events	Get list of events by jurisdiction.	try it!
/events/{event_id}	Get details on event by internal ID.	try it!
"""


params = {
        "include": ["organizations", "legislative_sessions", "latest_runs"]
}
headers = {
    "X-API-KEY": PLURAL_API_KEY
}
response = requests.get(
    f"{PLURAL_HOST}/people",
    headers=headers,
    params=params
)

page = response.json()

print(json.dumps(page, indent=4))