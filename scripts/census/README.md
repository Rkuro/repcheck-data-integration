# Census downloads

This folder includes downloads and ingestion into postgres for the following geographical areas:
1. Federal Senate Districts
2. Federal House Districts
3. State Senate Districts
4. State House Districts


Each is broken into its own file and follows roughly the same structure. Data is downloaded from the census tiger files: https://www2.census.gov/geo/tiger/TIGER2024/

Note: The federal house district downloader must be updated every two years to accommodate the new congress


## Usage

From the root of the project, you can run each like so:

```bash
# Setup venv
python -m venv venv
source .venv/bin/activate
pip install -r requirements.txt

python -m scripts.census.federal_house_districts
```

## Schemas
Schemas can be found in scripts/database/models.py
