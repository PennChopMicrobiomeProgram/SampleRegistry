# SampleRegistry

Library for adding/modifying/deleting sequencing runs and associated metadata with a Flask site for viewing data.



## Development

To start with local development:

```
git clone https://github.com/PennChopMicrobiomeProgram/SampleRegistry.git
cd SampleRegistry
python -m venv env/
source env/bin/activate
pip install -r requirements.txt
pip install app/sample_registry

create_test_db
export FLASK_DEBUG=1 && flask --app app/app run
```

## Deployment

How you want to deploy this will depend on your needs, facilities, and ability. We have it deployed by a Kubernetes cluster but you could also 1) just run it in development mode from a lab computer or 2) setup Nginx/Apache on a dedicated server or 3) run it serverlessly in the cloud (e.g. with [Zappa](https://github.com/zappa/Zappa) on AWS) or 4) do something else. There are lots of well documented examples of deploying Flask sites out there, look around and find what works best for you.

When running, it will default to using a SQLite3 database located in the root of this repository (automatically created if it doesn't already exist). You can change to a PostgreSQL backend by providing the environment variables DB_HOST, DB_NAME, DB_USER, and DB_PSWD. If you want to use a different backend, you'll have to do a bit of modification to ``app/sample_registry/src/sample_registry/__init__.py`` and be somewhat familiar with SQLAlchemy URI strings.