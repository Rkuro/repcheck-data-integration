

def convert_area_id(area_id: str):
    area_id = area_id.replace("jurisdiction", "division")
    area_id = area_id.replace("/government", "")
    return area_id