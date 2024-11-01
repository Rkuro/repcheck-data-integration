from sqlalchemy.orm import sessionmaker
import logging
from pathlib import Path
from dotenv import load_dotenv
from urllib import parse
from sqlalchemy import create_engine
import os

log = logging.getLogger(__name__)

parent_dir = Path(__file__).resolve().parent.parent.parent
env_path = parent_dir / '.env'
log.info(f"Loading .env from {env_path}")
load_dotenv(dotenv_path=env_path)

POSTGRES_DB_PASSWORD = os.getenv("POSTGRES_DB_PASSWORD")

# Define connection parameters
connection_params = {
    'username': 'postgres',
    'password': parse.quote(POSTGRES_DB_PASSWORD),
    'host': 'localhost',  # or '127.0.0.1'
    'port': '5432',  # Default PostgreSQL port
    'database': 'repcheck'
}


def get_engine():
    # Create an engine using key-value parameters
    engine = create_engine(
        f"postgresql+psycopg2://{connection_params['username']}:{connection_params['password']}@{connection_params['host']}:{connection_params['port']}/{connection_params['database']}"
    )
    return engine