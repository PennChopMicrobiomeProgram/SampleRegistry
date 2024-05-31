from typing import Generator
import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from src.sample_registry.db import create_test_db
from src.sample_registry.mapping import SampleTable
from src.sample_registry.models import (
    Annotation,
    Base,
    Sample,
    StandardHostSpecies,
    StandardSampleType,
)
from src.sample_registry.registrar import SampleRegistry

recs = [
    {
        "SampleID": "S1",
        "BarcodeSequence": "GCCT",
        "HostSpecies": "Human",  # Doesn't count towards annotations count, is stored in Sample
        "SubjectID": "Hu23",
    },
    {
        "SampleID": "S2",
        "BarcodeSequence": "GCAT",
        "key1": "val1",  # Counts towards annotations count
        "key2": "val2",
    },
]


@pytest.fixture()
def db() -> Generator[Session, None, None]:
    # This fixture should run before every test and create a new in-memory SQLite test database with identical data
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    engine = create_engine(SQLALCHEMY_DATABASE_URI, echo=False)
    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    session = Session()

    create_test_db(session)

    yield session

    session.rollback()
    session.close()


def test_check_run_accession(db):
    registry = SampleRegistry(db)
    assert registry.check_run_accession(1).run_accession == 1


def test_check_run_accession_doesnt_exist(db):
    registry = SampleRegistry(db)
    with pytest.raises(ValueError):
        registry.check_run_accession(9999)


def test_register_run(db):
    registry = SampleRegistry(db)
    assert (
        registry.register_run(
            "2021-01-01",
            "Illumina-MiSeq",
            "Nextera XT",
            1,
            "/path/to/data/",
            "A comment",
        )
        == 3
    )


def test_register_samples(db):
    registry = SampleRegistry(db)
    sample_table = SampleTable(recs)
    registry.register_samples(3, sample_table)

    assert (
        db.scalar(
            select(func.count(Sample.sample_accession)).where(Sample.run_accession == 3)
        )
        == 2
    )


def test_register_samples_already_registered(db):
    registry = SampleRegistry(db)
    sample_table = SampleTable(recs)
    registry.register_samples(3, sample_table)
    with pytest.raises(ValueError):
        registry.register_samples(3, sample_table)


def test_remove_samples(db):
    registry = SampleRegistry(db)
    sample_accessions = registry.remove_samples(1)
    assert not db.scalar(select(Sample).where(Sample.run_accession == 1))
    assert not db.scalar(
        select(Annotation).where(Annotation.sample_accession.in_(sample_accessions))
    )


def test_register_annotations(db):
    registry = SampleRegistry(db)
    sample_table = SampleTable(recs)
    registry.register_samples(3, sample_table)
    registry.register_annotations(3, sample_table)

    assert (
        db.scalar(
            select(func.count(Annotation.sample_accession)).where(
                Annotation.sample_accession == 3
            )
        )
        == 2
    )


def test_register_standard_sample_types(db):
    registry = SampleRegistry(db)
    registry.register_standard_sample_types([("type1", "common", False)])
    assert db.scalar(
        select(StandardSampleType).where(StandardSampleType.sample_type == "type1")
    )


def test_remove_standard_sample_types(db):
    registry = SampleRegistry(db)
    registry.remove_standard_sample_types()
    assert not db.scalar(select(StandardSampleType))


def test_register_standard_host_species(db):
    registry = SampleRegistry(db)
    registry.register_standard_host_species([("species1", "Species specius", 1)])
    assert db.scalar(
        select(StandardHostSpecies).where(
            StandardHostSpecies.host_species == "species1"
        )
    )


def test_remove_standard_host_species(db):
    registry = SampleRegistry(db)
    registry.remove_standard_host_species()
    assert not db.scalar(select(StandardHostSpecies))
