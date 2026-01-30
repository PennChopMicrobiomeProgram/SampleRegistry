# SampleRegistry

Library for adding/modifying/deleting sequencing runs and associated metadata with a Flask site for viewing data.

[![Tests](https://github.com/PennChopMicrobiomeProgram/SampleRegistry/actions/workflows/pr.yml/badge.svg)](https://github.com/PennChopMicrobiomeProgram/SampleRegistry/actions/workflows/pr.yml)
[![Codacy Badge](https://app.codacy.com/project/badge/Grade/5086d0c90973460a82b72ac90dfe3199)](https://app.codacy.com/gh/PennChopMicrobiomeProgram/SampleRegistry/dashboard?utm_source=gh&utm_medium=referral&utm_content=&utm_campaign=Badge_grade)
[![codecov](https://codecov.io/gh/PennChopMicrobiomeProgram/SampleRegistry/graph/badge.svg?token=ONUY5PYY9W)](https://codecov.io/gh/PennChopMicrobiomeProgram/SampleRegistry)
[![DockerHub](https://img.shields.io/docker/pulls/ctbushman/sample_registry)](https://hub.docker.com/repository/docker/ctbushman/sample_registry/)

## Development

To start with local development:

```
git clone https://github.com/PennChopMicrobiomeProgram/SampleRegistry.git
cd SampleRegistry
python -m venv env/
source env/bin/activate
pip install -e .[dev,web]

create_test_db
python sample_registry/app.py
```

## Deployment

How you want to deploy this will depend on your needs, facilities, and ability. We have it deployed by a Kubernetes cluster but you could also 1) just run it in development mode from a lab computer or 2) setup Nginx/Apache on a dedicated server or 3) run it serverlessly in the cloud (e.g. with [Zappa](https://github.com/zappa/Zappa) on AWS) or 4) do something else. There are lots of well documented examples of deploying Flask sites out there, look around and find what works best for you.

When running, it will default to using a SQLite3 database located in the root of this repository (automatically created if it doesn't already exist). You can change to use a different backend by setting the `SAMPLE_REGISTRY_DB_URI` environment variable before running the app. For example, another sqlite database could be specified with a URI like this: `export SAMPLE_REGISTRY_DB_URI=sqlite:////path/to/db.sqlite`.

If you're deploying behind a reverse proxy at a URL prefix, set `SAMPLE_REGISTRY_URL_PREFIX` (for example, `/sample_registry`). The WSGI entrypoint `sample_registry.app:application` will mount the Flask app at that prefix while leaving local development (`python sample_registry/app.py`) available at `/`.

## Using the library

The `sample_registry` library can be installed and run anywhere by following the instructions in Development (you don't need to do the `create_test_db` and running the site (bottom two commands)). To connect to a non-dev backend, see the above on SQLAlchemy URIs.

## Manually build Docker image

If you want to iterate over a feature you can only test on the K8s deployment, you can manually build the Docker image instead of relying on the release workflow. Use `docker build -t ctbushman/sample_registry:latest -f Dockerfile .` to build the image and then `docker push ctbushman/sample_registry:latest` to push it to DockerHub. You can then trigger the K8s deployment to grab the new image.

N.B. You might want to use a different tag than `latest` if you're testing something volatile so that if someone else is trying to use the image as you're developing, they won't pull your wonky changes.
