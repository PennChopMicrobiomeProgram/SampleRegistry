import gzip
import io
import os
import pytest
import tempfile
from sqlalchemy import and_, create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from typing import Generator
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
from src.sample_registry.register import (
    register_run,
    register_sample_annotations,
    unregister_samples,
    register_illumina_file,
    register_sample_types,
    register_host_species,
)


samples = [
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

modified_samples = [
    {
        "SampleID": "abc123",
        "BarcodeSequence": "GGGCCT",
        "SampleType": "Feces",
        "fg": "hi5 34",
    }
]

run_args = [
    "abc",
    "--lane",
    "1",
    "--date",
    "2008-09-21",
    "--type",
    "Illumina-MiSeq",
    "--comment",
    "mdsnfa adsf",
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


@pytest.fixture
def temp_sample_file():
    f = tempfile.NamedTemporaryFile(mode="wt")
    t = SampleTable(samples)
    t.write(f)
    f.seek(0)
    return f


@pytest.fixture
def temp_modified_sample_file():
    f = tempfile.NamedTemporaryFile(mode="wt")
    t = SampleTable(modified_samples)
    t.write(f)
    f.seek(0)
    return f


def test_register_run(db, temp_sample_file):
    out = io.StringIO()
    register_run(run_args, db, out)

    # Check that accession number is printed
    assert out.getvalue() == "Registered run 3 in the database\n"

    run = db.scalar(select(Run).where(Run.run_accession == 3))
    assert run.lane == 1
    assert run.run_date == "2008-09-21"
    assert run.machine_type == "Illumina-MiSeq"
    assert run.comment == "mdsnfa adsf"


def test_register_illumina_file(tmpdir, db):
    fastq_dir = "Miseq/160511_M03543_0047_000000000-APE6Y/Data/Intensities/" "BaseCalls"
    fastq_name = "Undetermined_S0_L001_R1_001.fastq.gz"

    os.makedirs(os.path.join(tmpdir, fastq_dir))
    relative_fp = os.path.join(fastq_dir, fastq_name)
    absolute_fp = os.path.join(tmpdir, relative_fp)
    with gzip.open(absolute_fp, "wt") as f:
        f.write("@M03543:21:C8LJ2ANXX:1:2209:1084:2044 1:N:0:NNNNNNNN+NNNNNNNN")

    out = io.StringIO()
    original_cwd = os.getcwd()
    os.chdir(tmpdir)
    try:
        register_illumina_file([relative_fp, "abcd efg"], db, out)
    finally:
        os.chdir(original_cwd)

    assert db.scalar(select(Run.data_uri).where(Run.run_accession == 3)) == relative_fp


def test_register_samples(db, temp_sample_file):
    register_run(run_args, db)
    sample_file = temp_sample_file
    args = ["3", sample_file.name]
    register_sample_annotations(args, True, db)

    # Check that accession number is assigned
    assert db.scalars(
        select(Sample.sample_accession).where(Sample.run_accession == 3)
    ).all() == [5, 6]
    assert (
        db.scalar(select(Sample.barcode_sequence).where(Sample.sample_accession == 5))
        == "GGGCCT"
    )
    # Check that standard annotations are saved to the database
    assert (
        db.scalar(select(Sample.sample_type).where(Sample.sample_accession == 5))
        == "Oral swab"
    )
    # Check that annotations are saved to the database
    assert (
        db.scalar(
            select(Annotation.val).where(
                and_(Annotation.sample_accession == 5, Annotation.key == "bb")
            )
        )
        == "cd e29"
    )
    assert (
        db.scalar(
            select(Annotation.val).where(
                and_(Annotation.sample_accession == 5, Annotation.key == "ll")
            )
        )
        == "mno 1"
    )

    # Check that the second sample is registered
    assert (
        db.scalar(select(Sample.barcode_sequence).where(Sample.sample_accession == 6))
        == "TTTCCC"
    )
    assert (
        db.scalar(select(Sample.sample_type).where(Sample.sample_accession == 6))
        == "Blood"
    )
    assert (
        db.scalar(
            select(Annotation.val).where(
                and_(Annotation.sample_accession == 6, Annotation.key == "bb")
            )
        )
        == "asdf"
    )


def test_register_annotations(db, temp_sample_file, temp_modified_sample_file):
    register_run(run_args, db)
    sample_file = temp_sample_file
    args = ["3", sample_file.name]
    register_sample_annotations(args, True, db)

    sample_file = temp_modified_sample_file
    args = ["3", sample_file.name]
    register_sample_annotations(args, False, db)

    # Check that the first sample is updated
    assert (
        db.scalar(select(Sample.sample_type).where(Sample.sample_accession == 5))
        == "Feces"
    )
    assert (
        db.scalar(
            select(Annotation.val).where(
                and_(Annotation.sample_accession == 5, Annotation.key == "fg")
            )
        )
        == "hi5 34"
    )
    assert not db.scalar(
        select(Annotation.val).where(
            and_(Annotation.sample_accession == 5, Annotation.key == "bb")
        )
    )


def test_unregister_samples(db, temp_sample_file):
    register_run(run_args, db)
    sample_file = temp_sample_file
    args = ["3", sample_file.name]
    register_sample_annotations(args, True, db)

    unregister_samples(["3"], db)

    assert not db.scalar(select(Sample).where(Sample.run_accession == 3))
    assert not db.scalar(select(Annotation).where(Annotation.sample_accession == 5))
    assert not db.scalar(select(Annotation).where(Annotation.sample_accession == 6))


def test_register_sample_types(db):
    f = tempfile.NamedTemporaryFile("wt")
    f.write(SAMPLE_TYPES_TSV)
    f.seek(0)

    register_sample_types([f.name], db)
    assert db.scalars(select(StandardSampleType.sample_type)).all() == [
        "Colonic biopsy",
        "Feces",
        "Oral wash",
        "Ostomy fluid",
        "Rectal swab",
    ]

    # Add a new sample type and re-register
    new_line = "Extra type\tCommon\t1\tJust to test"
    f2 = tempfile.NamedTemporaryFile("wt")
    f2.write(SAMPLE_TYPES_TSV + new_line)
    f2.seek(0)

    register_sample_types([f2.name], db)
    assert db.scalars(select(StandardSampleType.sample_type)).all() == [
        "Colonic biopsy",
        "Extra type",
        "Feces",
        "Oral wash",
        "Ostomy fluid",
        "Rectal swab",
    ]


def test_register_host_species(db):
    f = tempfile.NamedTemporaryFile("wt")
    f.write(HOST_SPECIES_TSV)
    f.seek(0)

    register_host_species([f.name], db)
    assert db.scalars(select(StandardHostSpecies.host_species)).all() == [
        "Human",
        "Mouse",
    ]

    # Add a new host species and re-register
    new_line = "Dog\tCanis lupus\t9615"
    f2 = tempfile.NamedTemporaryFile("wt")
    f2.write(HOST_SPECIES_TSV + new_line)
    f2.seek(0)

    register_host_species([f2.name], db)
    assert db.scalars(select(StandardHostSpecies.host_species)).all() == [
        "Dog",
        "Human",
        "Mouse",
    ]


SAMPLE_TYPES_TSV = """\
sample_type\trarity\thost_associated\tdescription

# Gut
Feces\tCommon\t1\tHuman and animal fecal material.\tNA
Rectal swab\tCommon\t1\tResults are sensitive to collection method.\tNA
Ostomy fluid\tCommon\t1\tNA
Colonic biopsy\tCommon\t1\tNA

# Oral
Oral wash\tCommon\t1\tNA
"""

HOST_SPECIES_TSV = """\
host_species\tscientific_name\tncbi_taxid
Human\tHomo sapiens\t9606
Mouse\tMus musculus\t10090
"""
