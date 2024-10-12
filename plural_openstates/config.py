import os
from pathlib import Path
import logging
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,  # Set the minimum logging level
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',  # Log message format
    datefmt='%Y-%m-%d %H:%M:%S',  # Date format
    handlers=[
        logging.StreamHandler()
    ]
)

parent_dir = Path(__file__).resolve().parent.parent
env_path = parent_dir / '.env'

log = logging.getLogger(__name__)
log.info(f"Loading .env from {env_path}")
load_dotenv(dotenv_path=env_path)

PLURAL_HOST = "https://v3.openstates.org"

PLURAL_API_KEY = os.getenv("PLURAL_API_KEY")