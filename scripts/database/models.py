from sqlmodel import SQLModel, Field, Relationship
from geoalchemy2 import Geometry
from sqlalchemy import Column, ARRAY, Text, JSON, BigInteger, DOUBLE_PRECISION
from typing import List, Optional, Dict


class Zipcode(SQLModel, table=True):
    __tablename__ = 'zipcodes'
    
    zip_code: str = Field(primary_key=True, nullable=False)
    geometry: Optional[Geometry] = Field(
        sa_column=Column(Geometry("POLYGON", srid=4326), nullable=True)
    )

    class Config:
        arbitrary_types_allowed = True


class Jurisdiction(SQLModel, table=True):
    __tablename__ = 'jurisdictions'

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
    jurisdiction_id: str = Field(foreign_key="jurisdictions.id", nullable=False)
    chamber: str
    name: str
    first_name: str
    last_name: str
    other_names: Optional[List[str]] = Field(default=None, sa_column=Column(ARRAY(Text)))
    party: str
    image: Optional[str] = None
    email: Optional[str] = None
    offices:Optional[List[Dict]] = Field(default=None, sa_column=Column(JSON))
    links: Optional[List[Dict]] = Field(default=None, sa_column=Column(JSON))
    ids: Optional[Dict] = Field(default=None, sa_column=Column(JSON))
    sources: Optional[List[Dict]] = Field(default=None, sa_column=Column(JSON))


