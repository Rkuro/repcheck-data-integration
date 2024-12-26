
def district_number_helper(classification, state_info, district_number):
    # Some edge cases here
    #
    # 1. Alaska has alphabetical districts for state senate
    # 2. AK, DC, DE, ND, SD, VT, WY have "at-large" districts for federal house of reps
    #     - We are going to denote this as "at-large" as the district number
    # 3. MD, MN, ND, SD, VT state houses have "subdistricts" e.g. 27 -> 27A, 27B, 27C
    if classification == "federal_house_district" and state_info["abbreviation"] in ["AK", "DC", "DE", "ND", "SD", "VT", "WY"]:
        return "at-large"

    try:
        return str(int(district_number)).lstrip("0")
    except ValueError:
        return str(district_number).lstrip("0")