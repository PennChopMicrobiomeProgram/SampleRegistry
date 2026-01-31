import importlib
import io

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from sample_registry.mapping import SampleTable
from sample_registry.models import Annotation, Base, Run, Sample

SAMPLES = [
    {
        "SampleID": "abc123",
        "BarcodeSequence": "GGGCCT",
        "SampleType": "Oral swab",
        "bb": "cd e29",
        "ll": "mno 1",
    },
    {
        "SampleID": "def456",
        "BarcodeSequence": "TTTCCC",
        "SampleType": "Blood",
        "bb": "asdf",
    },
]

MODIFIED_SAMPLES = [
    {
        "SampleID": "abc123",
        "BarcodeSequence": "GGGCCT",
        "SampleType": "Feces",
        "fg": "hi5 34",
    }
]


def _sample_table_payload(records):
    table = SampleTable(records)
    buf = io.StringIO()
    table.write(buf)
    return buf.getvalue()


@pytest.fixture
def api_client(tmp_path, monkeypatch):
    db_path = tmp_path / "registry.sqlite"
    uri = f"sqlite:///{db_path}"
    monkeypatch.setenv("SAMPLE_REGISTRY_DB_URI", uri)
    monkeypatch.delenv("PYTEST_VERSION", raising=False)
    engine = create_engine(uri, echo=False)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    create_test_db = importlib.import_module("sample_registry.db").create_test_db
    create_test_db(session)
    session.close()

    sample_registry = importlib.import_module("sample_registry")
    importlib.reload(sample_registry)
    import sample_registry.app as app_module

    app_module = importlib.reload(app_module)
    app_module.app.testing = True
    return app_module.app.test_client(), Session


def test_http_access_root(api_client):
    client, _ = api_client
    response = client.get("/")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/runs")


def test_api_register_run(api_client):
    client, Session = api_client
    response = client.post(
        "/api/register_run",
        json={
            "file": "raw/run4.fastq.gz",
            "date": "2024-08-01",
            "comment": "new run",
            "type": "Illumina-MiSeq",
            "lane": 1,
        },
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "ok"
    assert payload["run_accession"] == 4

    session = Session()
    try:
        run = session.scalar(select(Run).where(Run.run_accession == 4))
        assert run.comment == "new run"
        assert run.machine_type == "Illumina-MiSeq"
    finally:
        session.close()


def test_api_register_samples(api_client):
    client, Session = api_client
    client.post(
        "/api/register_run",
        json={
            "file": "raw/run4.fastq.gz",
            "date": "2024-08-01",
            "comment": "new run",
        },
    )
    payload = {
        "run_accession": 4,
        "sample_table": _sample_table_payload(SAMPLES),
    }
    response = client.post("/api/register_samples", json=payload)
    assert response.status_code == 200
    assert response.get_json()["sample_count"] == 2

    session = Session()
    try:
        samples = session.scalars(
            select(Sample)
            .where(Sample.run_accession == 4)
            .order_by(Sample.sample_accession)
        ).all()
        assert [s.sample_accession for s in samples] == [6, 7]
        assert samples[0].sample_type == "Oral swab"
    finally:
        session.close()


def test_api_register_annotations(api_client):
    client, Session = api_client
    client.post(
        "/api/register_run",
        json={
            "file": "raw/run4.fastq.gz",
            "date": "2024-08-01",
            "comment": "new run",
        },
    )
    client.post(
        "/api/register_samples",
        json={
            "run_accession": 4,
            "sample_table": _sample_table_payload(SAMPLES),
        },
    )
    response = client.post(
        "/api/register_annotations",
        json={
            "run_accession": 4,
            "sample_table": _sample_table_payload(MODIFIED_SAMPLES),
        },
    )
    assert response.status_code == 200

    session = Session()
    try:
        sample = session.scalar(select(Sample).where(Sample.sample_accession == 6))
        assert sample.sample_type == "Feces"
        annotation = session.scalar(
            select(Annotation).where(
                Annotation.sample_accession == 6, Annotation.key == "fg"
            )
        )
        assert annotation.val == "hi5 34"
    finally:
        session.close()


def test_api_unregister_samples(api_client):
    client, Session = api_client
    client.post(
        "/api/register_run",
        json={
            "file": "raw/run4.fastq.gz",
            "date": "2024-08-01",
            "comment": "new run",
        },
    )
    client.post(
        "/api/register_samples",
        json={
            "run_accession": 4,
            "sample_table": _sample_table_payload(SAMPLES),
        },
    )
    response = client.post("/api/unregister_samples", json={"run_accession": 4})
    assert response.status_code == 200

    session = Session()
    try:
        assert not session.scalar(select(Sample).where(Sample.run_accession == 4))
    finally:
        session.close()


def test_api_modify_run(api_client):
    client, Session = api_client
    client.post(
        "/api/register_run",
        json={
            "file": "raw/run4.fastq.gz",
            "date": "2024-08-01",
            "comment": "new run",
        },
    )
    response = client.post(
        "/api/modify_run",
        json={
            "run_accession": 4,
            "comment": "updated",
            "lane": 2,
        },
    )
    assert response.status_code == 200

    session = Session()
    try:
        run = session.scalar(select(Run).where(Run.run_accession == 4))
        assert run.comment == "updated"
        assert run.lane == 2
    finally:
        session.close()


def test_api_modify_sample(api_client):
    client, Session = api_client
    response = client.post(
        "/api/modify_sample",
        json={
            "sample_accession": 1,
            "sample_name": "Sample1-updated",
            "subject_id": "Subject1a",
        },
    )
    assert response.status_code == 200

    session = Session()
    try:
        sample = session.scalar(select(Sample).where(Sample.sample_accession == 1))
        assert sample.sample_name == "Sample1-updated"
        assert sample.subject_id == "Subject1a"
    finally:
        session.close()


def test_api_modify_annotation(api_client):
    client, Session = api_client
    response = client.post(
        "/api/modify_annotation",
        json={"sample_accession": 1, "key": "key0", "val": "updated"},
    )
    assert response.status_code == 200

    session = Session()
    try:
        annotation = session.scalar(
            select(Annotation).where(
                Annotation.sample_accession == 1, Annotation.key == "key0"
            )
        )
        assert annotation.val == "updated"
    finally:
        session.close()
