
def district_number_helper(district_number):
    # Alaska has alphabetical districts for state senate cuz of course alaska :rolling-eyes:
    try:
        return str(int(district_number))
    except ValueError:
        return district_number.lstrip('0').lower() # We don't want '001' - we want '1'
