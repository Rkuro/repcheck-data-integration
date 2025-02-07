from sqlmodel import SQLModel, Field, Relationship
from geoalchemy2 import Geometry
from datetime import datetime, timezone
from sqlalchemy import Column, ARRAY, Text, BigInteger, DOUBLE_PRECISION, DateTime, text
from sqlalchemy.dialects.postgresql import JSONB
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

class PrecinctElectionResultArea(SQLModel, table=True):
    __tablename__ = "precinct_election_result_area"
    precinct_id: str = Field(primary_key=True, nullable=False)
    state: str
    votes_dem: int = Field(sa_column=Column(BigInteger()))
    votes_rep: int = Field(sa_column=Column(BigInteger()))
    votes_total: int = Field(sa_column=Column(BigInteger()))
    pct_dem_lead: float = Field(sa_column=Column(DOUBLE_PRECISION()))
    official_boundary: Optional[bool]
    geometry: Geometry = Field(sa_column=Column(Geometry("GEOMETRY", srid=4326), nullable=False))
    centroid_lat: float = Field(sa_column=Column(DOUBLE_PRECISION()))
    centroid_lon: float = Field(sa_column=Column(DOUBLE_PRECISION()))

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
    offices:Optional[List[Dict]] = Field(default=None, sa_column=Column(JSONB))
    links: Optional[List[Dict]] = Field(default=None, sa_column=Column(JSONB))
    ids: Optional[Dict] = Field(default=None, sa_column=Column(JSONB))
    sources: Optional[List[Dict]] = Field(default=None, sa_column=Column(JSONB))


class Bill(SQLModel, table=True):
    __tablename__ = 'bills'

    id: str = Field(primary_key=True, nullable=False)
    title: str
    canonical_id: str
    jurisdiction_area_id: str = Field(foreign_key="areas.id", nullable=False)
    legislative_session: str
    from_organization:Dict = Field(default=None, sa_column=Column(JSONB))
    classification: List[str] = Field(default=None, sa_column=Column(JSONB))
    subject: List[Dict] = Field(default=None, sa_column=Column(JSONB))
    abstracts: List[Dict] = Field(default=None, sa_column=Column(JSONB))
    other_titles: List[Dict] = Field(default=None, sa_column=Column(JSONB))
    other_identifiers: List[str] = Field(default=None, sa_column=Column(JSONB))
    actions: List[Dict] = Field(default=None, sa_column=Column(JSONB))
    sponsorships: List[Dict] = Field(default=None, sa_column=Column(JSONB))
    related_bills: List[Dict] = Field(default=None, sa_column=Column(JSONB))
    versions: List[Dict] = Field(default=None, sa_column=Column(JSONB))
    documents: List[Dict] = Field(default=None, sa_column=Column(JSONB))
    citations: List[Dict] = Field(default=None, sa_column=Column(JSONB))
    sources: List[Dict] = Field(default=None, sa_column=Column(JSONB))
    extras: Dict = Field(default=None, sa_column=Column(JSONB))

    # Derived fields
    latest_action_date: Optional[datetime] = Field(default=None, sa_column=Column(DateTime))
    first_action_date: Optional[datetime] = Field(default=None, sa_column=Column(DateTime))
    updated_at: datetime = Field(default=None, sa_column=Column(DateTime))
    created_at: datetime = Field(sa_column_kwargs={"server_default": text("CURRENT_TIMESTAMP")})
    jurisdiction_level: str


class VoteEvent(SQLModel, table=True):
    __tablename__ = 'vote_events'

    id: str = Field(primary_key=True, nullable=False)
    bill_id: str = Field(foreign_key="bills.id", nullable=False)
    identifier: str
    motion_text: str
    motion_classification: List[str] = Field(default=None, sa_column=Column(JSONB))
    start_date: datetime
    result: str
    chamber: str
    legislative_session: str
    votes: List[Dict] = Field(default=None, sa_column=Column(JSONB))
    counts: List[Dict] = Field(default=None, sa_column=Column(JSONB))
    sources: List[Dict] = Field(default=None, sa_column=Column(JSONB))
    extras: Dict = Field(default=None, sa_column=Column(JSONB))

