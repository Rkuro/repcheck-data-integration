from sqlalchemy import (
    Column,
    Integer,
    ForeignKey,
    Date,
    Text,
    ARRAY,
    DateTime
)
from sqlalchemy.dialects.postgresql import VARCHAR, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from geoalchemy2 import Geometry


# Set up SQLAlchemy base and engine
Base = declarative_base()

class Zipcode(Base):
    __tablename__ = 'zipcodes'
    
    zip_code = Column(VARCHAR(100), primary_key=True, nullable=False)
    geometry = Column(Geometry('POLYGON', srid=4326), nullable=True)
    
    # Define relationships if needed
    zipcode_people = relationship(
        "ZipcodePeopleJoinTable",
        back_populates="zipcode",
        cascade="all, delete",
    )

class ZipcodePeopleJoinTable(Base):
    __tablename__ = 'zipcode_people_join_table'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    zip_code = Column(VARCHAR(100), ForeignKey('zipcodes.zip_code', ondelete='CASCADE'))
    person_id = Column(VARCHAR(100), ForeignKey('people.id', ondelete='CASCADE'))
    
    # Define relationships
    zipcode = relationship("Zipcode", back_populates="zipcode_people")
    person = relationship("Person", back_populates="zipcode_people")

class Person(Base):
    __tablename__ = 'people'
    
    id = Column(VARCHAR(255), primary_key=True, nullable=False)
    name = Column(VARCHAR(255), nullable=False)
    current_party = Column(VARCHAR(100), nullable=True)
    current_district = Column(VARCHAR(255), nullable=True)
    current_chamber = Column(VARCHAR(100), nullable=True)
    given_name = Column(VARCHAR(100), nullable=True)
    family_name = Column(VARCHAR(100), nullable=True)
    gender = Column(VARCHAR(20), nullable=True)
    email = Column(VARCHAR(255), nullable=True)
    biography = Column(Text, nullable=True)
    birth_date = Column(Date, nullable=True)
    death_date = Column(Date, nullable=True)
    image = Column(Text, nullable=True)
    links = Column(ARRAY(Text), nullable=True)
    sources = Column(ARRAY(Text), nullable=True)
    capitol_address = Column(Text, nullable=True)
    capitol_voice = Column(VARCHAR(20), nullable=True)
    capitol_fax = Column(VARCHAR(20), nullable=True)
    district_address = Column(Text, nullable=True)
    district_voice = Column(VARCHAR(20), nullable=True)
    district_fax = Column(VARCHAR(20), nullable=True)
    twitter = Column(VARCHAR(100), nullable=True)
    youtube = Column(VARCHAR(100), nullable=True)
    instagram = Column(VARCHAR(100), nullable=True)
    facebook = Column(VARCHAR(100), nullable=True)
    wikidata = Column(VARCHAR(100), nullable=True)
    jurisdiction_id = Column(VARCHAR(255), nullable=True)
    
    # Define relationships if needed
    zipcode_people = relationship(
        "ZipcodePeopleJoinTable",
        back_populates="person",
        cascade="all, delete",
    )



class Bill(Base):
    __tablename__ = 'bills'
    id = Column(Text, primary_key=True)
    session = Column(Text)
    jurisdiction_id = Column(Text)
    jurisdiction = Column(JSONB)
    from_organization = Column(JSONB)
    identifier = Column(Text)
    title = Column(Text)
    classification = Column(JSONB)
    subject = Column(JSONB)
    extras = Column(JSONB)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    openstates_url = Column(Text)
    first_action_date = Column(DateTime)
    latest_action_date = Column(DateTime)
    latest_action_description = Column(Text)
    latest_passage_date = Column(DateTime)
    related_bills = Column(JSONB)
    abstracts = Column(JSONB)
    other_titles = Column(JSONB)
    other_identifiers = Column(JSONB)
    sponsorships = Column(JSONB)
    actions = Column(JSONB)
    sources = Column(JSONB)
    versions = Column(JSONB)
    documents = Column(JSONB)
    votes = Column(JSONB)

class Jurisdiction(Base):
    __tablename__ = 'jurisdictions'
    id = Column(Text, primary_key=True)
    name = Column(Text, nullable=True)
    classification = Column(Text, nullable=True)
    division_id = Column(Text, nullable=True)
    url = Column(Text, nullable=True)
    latest_bill_update = Column(DateTime, nullable=True)
    latest_people_update = Column(DateTime, nullable=True)
    organizations = Column(JSONB, nullable=True)
    legislative_sessions = Column(JSONB, nullable=True)
    latest_runs = Column(JSONB, nullable=True)
    last_processed = Column(DateTime, nullable=True)
