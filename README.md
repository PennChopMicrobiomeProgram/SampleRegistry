# SampleRegistry

Library for adding/modifying/deleting sequencing runs and associated metadata with a Flask site for viewing data.

[![Tests](https://github.com/PennChopMicrobiomeProgram/SampleRegistry/actions/workflows/pr.yml/badge.svg)](https://github.com/PennChopMicrobiomeProgram/SampleRegistry/actions/workflows/pr.yml)
[![Codacy Badge](https://app.codacy.com/project/badge/Grade/5086d0c90973460a82b72ac90dfe3199)](https://app.codacy.com/gh/PennChopMicrobiomeProgram/SampleRegistry/dashboard?utm_source=gh&utm_medium=referral&utm_content=&utm_campaign=Badge_grade)
[![codecov](https://codecov.io/gh/PennChopMicrobiomeProgram/SampleRegistry/graph/badge.svg?token=ONUY5PYY9W)](https://codecov.io/gh/PennChopMicrobiomeProgram/SampleRegistry)
[![DockerHub](https://img.shields.io/docker/pulls/chopmicrobiome/sample_registry)](https://hub.docker.com/repository/docker/chopmicrobiome/sample_registry/)

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

There are three ways of using the library utilities (register_run, register_samples, modify_run, etc):

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

## CLI usage

The project installs the following CLI commands:

- `register_run`
- `register_run_file`
- `register_samples`
- `register_annotations`
- `unregister_samples`
- `modify_run`
- `modify_sample`
- `modify_annotation`
- `export_samples`
- `create_test_db`
- `sample_registry_version`

Use `-h` on any command to show its arguments and examples:

```bash
register_run -h
modify_run -h
register_samples -h
```

Most commands read/write to the database configured by `SAMPLE_REGISTRY_DB_URI`. If this variable is not set, the default is a local SQLite database in the repository root.

Typical workflow:

```bash
# 1) register a run
register_run /path/to/run.fastq.gz --date 2024-09-25 --comment "MiSeq run"

# 2) register samples and annotations from a metadata table
# IF USING PODMAN:
# Temporarily copy the sample metadata table to this directory: mbiome.research.chop.edu:/var/local/sample_registry
# This path is where podman can find files and is mapped to '/data/'
register_samples <run_accession> /data/sample_metadata.tsv
register_annotations <run_accession> /data/sample_metadata.tsv

# If using local CLI, simply use the relative path to the run's sample metadata table tsv:
register_samples <run_accession> sample_metadata.tsv
register_annotations <run_accession> sample_metadata.tsv

# 3) make updates later
modify_run <run_accession> --comment "Updated comment"
modify_sample <sample_accession> --sample_name "New sample name"
```

## API usage

The Flask app exposes JSON API endpoints under `/api/*`. Write endpoints accept `POST` requests with `Content-Type: application/json`, and read endpoints accept `GET` requests with query parameters. All endpoints return JSON.

Available endpoints:

- `POST /api/register_run`
- `POST /api/register_samples`
- `POST /api/register_annotations`
- `POST /api/unregister_samples`
- `POST /api/modify_run`
- `POST /api/modify_sample`
- `POST /api/modify_annotation`
- `GET /api/get_run`
- `GET /api/get_runs_by_data_uri`
- `GET /api/get_samples`
- `GET /api/get_annotations`

Example API calls:

```bash
# Register a run
curl -X POST "https://mbiome.research.chop.edu/sample_registry/api/register_run" \
  -H "Content-Type: application/json" \
  -d '{
    "file": "/path/to/run.fastq.gz",
    "date": "2024-09-25",
    "comment": "MiSeq run",
    "lane": 1,
    "type": "Illumina-MiSeq"
  }'

# Modify a run
curl -X POST "https://mbiome.research.chop.edu/sample_registry/api/modify_run" \
  -H "Content-Type: application/json" \
  -d '{"run_accession": 1638, "comment": "Updated run comment"}'

# Modify a sample
curl -X POST "https://mbiome.research.chop.edu/sample_registry/api/modify_sample" \
  -H "Content-Type: application/json" \
  -d '{"sample_accession": 1042, "sample_name": "SampleABC"}'


# Get a run
curl -G "https://mbiome.research.chop.edu/sample_registry/api/get_run" \
  --data-urlencode "run_accession=1638"

# Get all samples for a run
curl -G "https://mbiome.research.chop.edu/sample_registry/api/get_samples" \
  --data-urlencode "run_accession=1638"


```

For metadata-table endpoints (`register_samples` and `register_annotations`), provide either:

- a JSON payload with a `sample_table` key containing tab-delimited data, or
- `multipart/form-data` with a file upload.
```bash
# register samples using tsv metadata
curl -X POST "https://mbiome.research.chop.edu/sample_registry/api/register_samples" \
  -H "Content-Type: application/json" \
  -d "$(python3 -c 'import json; print(json.dumps({"run_accession": 1697, "sample_table": open("mapping.tsv").read()}))')" 
  # make sure mapping.tsv is in your current dir where you run the command
```

On success, endpoints return `{"status": "ok", ...}`. Validation errors return `{"status": "error", "error": "..."}` with HTTP 400.

## Manually build Docker image

If you want to iterate over a feature you can only test on the K8s deployment, you can manually build the Docker image instead of relying on the release workflow. Use `docker build -t chopmicrobiome/sample_registry:latest -f Dockerfile .` to build the image and then `docker push chopmicrobiome/sample_registry:latest` to push it to DockerHub. You can then trigger the K8s deployment to grab the new image. You can do the same replacing `docker` with `podman` on mbiome.


N.B. You might want to use a different tag than `latest` (e.g. `chopmicrobiome/sample_registry:dev`) if you're testing something volatile so that if someone else is trying to use the image as you're developing, they won't pull your wonky changes.

