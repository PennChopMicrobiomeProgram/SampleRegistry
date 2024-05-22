# SampleRegistry

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

