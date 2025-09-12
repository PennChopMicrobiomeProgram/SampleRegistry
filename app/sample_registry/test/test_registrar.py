from typing import Generator
import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from src.sample_registry.db import create_test_db
from src.sample_registry.mapping import SampleTable
from src.sample_registry.models import (
    Annotation,
    Base,
    Run,
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


def test_get_run(db):
    registry = SampleRegistry(db)
    run = registry.get_run(1)
    assert run.run_accession == 1
    assert run.run_date == "2024-07-02"


def test_get_run_doesnt_exist(db):
    registry = SampleRegistry(db)
    assert registry.get_run(9999) is None


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
        == 4
    )


def test_modify_run(db):
    registry = SampleRegistry(db)
    registry.modify_run(1, run_date="12/12/12", machine_type="Illumina-MiSeq")
    assert db.scalar(select(Run).where(Run.run_accession == 1)).run_date == "12/12/12"


def test_check_samples(db):
    registry = SampleRegistry(db)
    assert len(registry.check_samples(1)) == 2


def test_check_samples_exist(db):
    registry = SampleRegistry(db)
    with pytest.raises(ValueError):
        registry.check_samples(1, exists=False)


def test_check_samples_doesnt_exist(db):
    registry = SampleRegistry(db)
    with pytest.raises(ValueError):
        registry.check_samples(9999)


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


def test_modify_samples(db):
    registry = SampleRegistry(db)
    registry.modify_sample(1, sample_name="New name")

    assert (
        db.scalar(select(Sample).where(Sample.sample_accession == 1)).sample_name
        == "New name"
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


def test_modify_annotation(db):
    registry = SampleRegistry(db)
    registry.modify_annotation(1, "key0", "new val")
    assert (
        db.scalar(
            select(Annotation).where(
                Annotation.sample_accession == 1, Annotation.key == "key0"
            )
        ).val
        == "new val"
    )


def test_register_standard_sample_types(db):
    registry = SampleRegistry(db)
    registry.register_standard_sample_types([("type1", "common", False, "NA")])
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
