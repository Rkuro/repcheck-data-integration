from sqlmodel import SQLModel, Field, Relationship
from geoalchemy2 import Geometry
from datetime import datetime
from sqlalchemy import Column, ARRAY, Text, JSON, BigInteger, DOUBLE_PRECISION
from typing import List, Optional, Dict

class PersonArea(SQLModel, table=True):
    __tablename__ = "person_area"

    person_id: str = Field(foreign_key="people.id", primary_key=True)
    area_id: str = Field(foreign_key="areas.id", primary_key=True)
    relationship_type: str # For ex: constituent_zip_code


class Area(SQLModel, table=True):
    __tablename__ = 'areas'

    # For convenience more than anything, we are opting to use
    # the "ocd-division/" prefix to identifiers for political districting, but I have mixed feelings about this
    id: str = Field(primary_key=True, nullable=False)
    classification: str
    name: str
    abbrev: Optional[str] = None
    fips_code: Optional[str] = None
    district_number: Optional[str] = None
    geo_id: Optional[str] = None
    geo_id_fq: Optional[str] = None
    legal_statistical_area_description_code: Optional[str] = None
    maf_tiger_feature_class_code: Optional[str] = None
    funcstat: Optional[str] = None
    land_area: int = Field(sa_column=Column(BigInteger()))
    water_area: int = Field(sa_column=Column(BigInteger()))
    centroid_lat: float = Field(sa_column=Column(DOUBLE_PRECISION()))
    centroid_lon: float = Field(sa_column=Column(DOUBLE_PRECISION()))
    geometry: Geometry = Field(sa_column=Column(Geometry("GEOMETRY", srid=4326), nullable=False))

    class Config:
        arbitrary_types_allowed = True


class Person(SQLModel, table=True):
    __tablename__ = 'people'
    
    id: str = Field(primary_key=True, nullable=False)
    jurisdiction_area_id: str = Field(foreign_key="areas.id", nullable=False)
    constituent_area_id: str = Field(foreign_key="areas.id", nullable=False)
    chamber: str
    name: str
    first_name: str
    last_name: str
    other_names: Optional[List[str]] = Field(default=None, sa_column=Column(ARRAY(Text)))
    image: Optional[str] = None
    email: Optional[str] = None
    offices:Optional[List[Dict]] = Field(default=None, sa_column=Column(JSON))
    links: Optional[List[Dict]] = Field(default=None, sa_column=Column(JSON))
    ids: Optional[Dict] = Field(default=None, sa_column=Column(JSON))
    sources: Optional[List[Dict]] = Field(default=None, sa_column=Column(JSON))


class Bill(SQLModel, table=True):
    __tablename__ = 'bills'

    id: str = Field(primary_key=True, nullable=False)
    title: str
    canonical_id: str
    jurisdiction_area_id: str = Field(foreign_key="areas.id", nullable=False)
    legislative_session: str
    from_organization:Dict = Field(default=None, sa_column=Column(JSON))
    classification: List[str] = Field(default=None, sa_column=Column(JSON))
    subject: List[Dict] = Field(default=None, sa_column=Column(JSON))
    abstracts: List[Dict] = Field(default=None, sa_column=Column(JSON))
    other_titles: List[Dict] = Field(default=None, sa_column=Column(JSON))
    other_identifiers: List[str] = Field(default=None, sa_column=Column(JSON))
    actions: List[Dict] = Field(default=None, sa_column=Column(JSON))
    sponsorships: List[Dict] = Field(default=None, sa_column=Column(JSON))
    related_bills: List[Dict] = Field(default=None, sa_column=Column(JSON))
    versions: List[Dict] = Field(default=None, sa_column=Column(JSON))
    documents: List[Dict] = Field(default=None, sa_column=Column(JSON))
    citations: List[Dict] = Field(default=None, sa_column=Column(JSON))
    sources: List[Dict] = Field(default=None, sa_column=Column(JSON))
    extras: Dict = Field(default=None, sa_column=Column(JSON))


class VoteEvent(SQLModel, table=True):
    __tablename__ = 'vote_events'

    id: str = Field(primary_key=True, nullable=False)
    bill_id: str = Field(foreign_key="bills.id", nullable=False)
    identifier: str
    motion_text: str
    motion_classification: List[str] = Field(default=None, sa_column=Column(JSON))
    start_date: datetime
    result: str
    chamber: str
    legislative_session: str
    votes: List[Dict] = Field(default=None, sa_column=Column(JSON))
    counts: List[Dict] = Field(default=None, sa_column=Column(JSON))
    sources: List[Dict] = Field(default=None, sa_column=Column(JSON))
    extras: Dict = Field(default=None, sa_column=Column(JSON))

