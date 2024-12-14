# repcheck-data-integration
Data integration code for repcheck


You need a .env file with:

Do not check this file into git!
```.env
POSTGRES_DB_PASSWORD = xxx
```

You can then run like so
```bash
# set up venv
python -m venv venv
source ./venv/bin/activate
pip install -r requirements.txt
python -m scripts.$script_name
```

Note: Repo assumes that postgres is running locally on the default 5432 port
and uses the database name 'repcheck' which must already exist!