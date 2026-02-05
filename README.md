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

flask --app sample_registry/app run --debug
```

## Deployment

The SampleRegistry lives on `mbiome` running under Podman. The SQLite database is located at `/var/local/sample_registry/sample_registry.sqlite`. Reference github.research.chop.edu/MicrobiomeCenter/deployments for more info.

When running, it will default to using a SQLite3 database located in the root of this repository (automatically created if it doesn't already exist). You can change to use a different backend by setting the `SAMPLE_REGISTRY_DB_URI` environment variable before running the app. For example, another sqlite database could be specified with a URI like this: `export SAMPLE_REGISTRY_DB_URI=sqlite:////path/to/db.sqlite`.

## Using the library

There are three ways of using the libraries utilities (register_run, register_samples, modify_run, etc):

1. Install this repo into your home directory on mbiome and run it directly from there:

```
ssh mbiome.research.chop.edu
git clone https://github.com/PennChopMicrobiomeProgram/SampleRegistry.git
cd SampleRegistry
python -m venv env
# For added convenience, I'd recommend adding SAMPLE_REGISTRY_DB_URI to your env permanently
# Edit the `activate` script and add a line at the bottom like this:
# export SAMPLE_REGISTRY_DB_URI=sqlite:////var/local/sample_registry/sample_registry.sqlite
source env/bin/activate
pip install -e .
# Test that it works
modify_run -h
```

2. Use the CLI of the version running in Podman:

```
ssh mbiome.research.chop.edu
sudo podman exec sample-registry modify_run -h
```

3. Use the API (behind the scenes, this also uses the CLI of the version running in Podman):

```
# From any computer on the CHOP network
curl -H "Content-Type: application/json" -d '{"run_accession": "1638", "comment": "CHOPMC-580 Ahmed Moustafa rerun 3 (10 pM)"}' https://mbiome.research.chop.edu/sample_registry/api/modify_run
```

## Manually build Docker image

If you want to iterate over a feature you can only test on the K8s deployment, you can manually build the Docker image instead of relying on the release workflow. Use `docker build -t ctbushman/sample_registry:latest -f Dockerfile .` to build the image and then `docker push ctbushman/sample_registry:latest` to push it to DockerHub. You can then trigger the K8s deployment to grab the new image. You can do the same replacing `docker` with `podman` on mbiome.


N.B. You might want to use a different tag than `latest` (e.g. `ctbushman/sample_registry:dev`) if you're testing something volatile so that if someone else is trying to use the image as you're developing, they won't pull your wonky changes.
