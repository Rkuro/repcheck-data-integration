import logging
from sqlalchemy.sql import select, func

from ..logging_config import setup_logging
from ..database.models import Person, Area, PersonArea
from ..database.database import get_session, upsert_dynamic

log = logging.getLogger(__name__)

def connect_zip_codes(session):
    # Zip codes are slightly odd in that since we are designing the UX
    # around them, we need to create some edges between them and other data:
    # Zip code -> Person (based on representative district area not jurisdiction)
    log.info("Connecting zip codes")
    people = session.exec(
        select(
            Person.id,
            Person.name,
            Person.constituent_area_id
        ).where(
            Person.jurisdiction_area_id=='ocd-division/country:us/district:dc'
        )
    ).all()

    num_people = len(people)

    for i, person in enumerate(people):
        constituent_area = session.exec(
            select(Area).where(Area.id == person.constituent_area_id)
        ).scalars().one_or_none()

        if not constituent_area:
            raise RuntimeError(f"No constituent area found for {person.name}")

        zip_code_areas = session.exec(
            select(Area).where(
                Area.classification == "zipcode",
                func.ST_Intersects(Area.geometry, constituent_area.geometry)
            )
        ).scalars().all()

        log.info(f"Connecting person {person.name} to zip codes. {i}/{num_people}. Zip Codes: {len(zip_code_areas)}")

        for zip_area in zip_code_areas:
            association = PersonArea(
                person_id=person.id,
                area_id=zip_area.id,
                relationship_type="constituent_area_zip_code"
            )
            # Write to db
            upsert_dynamic(session, association)

    session.commit()
    session.close()

def main():
    log.info("Connecting zip codes")

    # Setup
    with get_session() as session:
        connect_zip_codes(session)

if __name__ == "__main__":
    setup_logging()
    main()