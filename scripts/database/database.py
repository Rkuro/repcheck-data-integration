from sqlmodel import create_engine, Session, SQLModel, inspect
from sqlalchemy.dialects.postgresql import insert
import logging
from pathlib import Path
from dotenv import load_dotenv
from urllib.parse import quote
import os

log = logging.getLogger(__name__)

# Load dotenv variables
parent_dir = Path(__file__).resolve().parent.parent.parent
env_path = parent_dir / '.env'
log.info(f"Loading .env from {env_path}")
load_dotenv(dotenv_path=env_path)

POSTGRES_DB_PASSWORD = os.getenv("POSTGRES_DB_PASSWORD")

# Define connection parameters
connection_params = {
    'username': 'postgres',
    'password': quote(POSTGRES_DB_PASSWORD),
    'host': 'localhost',  # or '127.0.0.1'
    'port': '5432',  # Default PostgreSQL port
    'database': 'repcheck'
}

def get_engine():
    # Create an engine using SQLModel
    database_url = (
        f"postgresql+psycopg2://{connection_params['username']}:{connection_params['password']}"
        f"@{connection_params['host']}:{connection_params['port']}/{connection_params['database']}"
    )
    engine = create_engine(database_url)
    # Ensure all tables exist!
    SQLModel.metadata.create_all(engine)
    return engine


def get_session():
    engine = get_engine()
    session = Session(engine)
    return session

# Upsert any data into the DB - overwrites all fields if data exists already
def upsert_dynamic(session, data):
    # Get the model class from the instance
    model = type(data)

    # Convert instance to dictionary, excluding unset values
    data = data.dict(exclude_unset=True)
    mapper = inspect(model)
    primary_keys = [key.name for key in mapper.primary_key]

    # Prepare the insert statement
    stmt = insert(model).values(data)

    # Automatically exclude primary keys from the `SET` clause
    update_fields = {col.name: getattr(stmt.excluded, col.name)
                     for col in mapper.columns if col.name not in primary_keys}

    stmt = stmt.on_conflict_do_update(
        index_elements=primary_keys,
        set_=update_fields,
    )
    session.execute(stmt)
    session.commit()
