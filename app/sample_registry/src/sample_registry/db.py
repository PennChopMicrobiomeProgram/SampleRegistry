import csv
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import delete
from sqlalchemy.orm import sessionmaker
from .models import (
    Base,
    Run,
    Sample,
    Annotation,
    StandardSampleType,
    StandardHostSpecies,
)


STANDARD_TAGS = {
    "SampleType": "sample_type",
    "SubjectID": "subject_id",
    "HostSpecies": "host_species",
}


def create_test_db(session: sessionmaker = None):
    if not session:
        from . import engine
        from . import session as imported_session

        session = imported_session
        Base.metadata.create_all(engine)

    if session.query(Run).count() > 0:
        session.execute(delete(Run))
        session.execute(delete(Sample))
        session.execute(delete(Annotation))
        session.execute(delete(StandardSampleType))
        session.execute(delete(StandardHostSpecies))

    run1 = Run(
        run_accession=1,
        run_date=datetime.now(),
        machine_type="Illumina",
        machine_kit="MiSeq",
        lane=1,
        data_uri="run1",
        comment="Test run 1",
    )
    run2 = Run(
        run_accession=2,
        run_date=datetime.now(),
        machine_type="Illumina",
        machine_kit="MiSeq",
        lane=1,
        data_uri="run2",
        comment="Test run 2",
    )
    session.bulk_save_objects([run1, run2])

    sample1 = Sample(
        sample_accession=1,
        sample_name="Sample1",
        run_accession=run1.run_accession,
        barcode_sequence="AAAA",
        primer_sequence="TTTT",
        sample_type="BAL",
        subject_id="Subject1",
        host_species="Human",
    )
    sample2 = Sample(
        sample_accession=2,
        sample_name="Sample2",
        run_accession=run1.run_accession,
        barcode_sequence="CCCC",
        primer_sequence="GGGG",
        sample_type="Cecum",
        subject_id="Subject2",
        host_species="Human",
    )
    sample3 = Sample(
        sample_accession=3,
        sample_name="Sample3",
        run_accession=run2.run_accession,
        barcode_sequence="GGGG",
        primer_sequence="CCCC",
        sample_type="Whole gut",
        subject_id="Subject3",
        host_species="Human",
    )
    sample4 = Sample(
        sample_accession=4,
        sample_name="Sample4",
        run_accession=run2.run_accession,
        barcode_sequence="TTTT",
        primer_sequence="AAAA",
        sample_type="Urine",
        subject_id="Subject4",
        host_species="Human",
    )
    session.bulk_save_objects([sample1, sample2, sample3, sample4])

    annotations = [
        Annotation(
            sample_accession=sample.sample_accession, key=f"key{i}", val=f"val{i % 2}"
        )
        for i, sample in enumerate(
            [sample1, sample2, sample3, sample4, sample1, sample2, sample3, sample4]
        )
    ]
    session.bulk_save_objects(annotations)

    try:
        init_standard_sample_types(session)
    except FileNotFoundError:
        session.add(
            StandardSampleType(
                sample_type="Stool",
                rarity="Uncommon",
                host_associated=True,
                comment="Poo",
            )
        )
        session.add(
            StandardSampleType(
                sample_type="Blood",
                rarity="Common",
                host_associated=True,
                comment="Red stuff",
            )
        )

    try:
        init_standard_host_species(session)
    except FileNotFoundError:
        session.add(
            StandardHostSpecies(
                host_species="Human", scientific_name="Person", ncbi_taxon_id=1
            )
        )
        session.add(
            StandardHostSpecies(
                host_species="Mouse", scientific_name="FurryLittleDude", ncbi_taxon_id=2
            )
        )

    session.commit()


def init_standard_sample_types(session: sessionmaker):
    with open("standard_sample_types.tsv", "r") as file:
        reader = csv.reader(file, delimiter="\t")
        next(reader)  # Skip header row
        sample_types = []
        for row in reader:
            sample_type = row[0]
            rarity = row[1]
            host_associated = bool(row[2])
            comment = row[3]
            sample_types.append(
                StandardSampleType(
                    sample_type=sample_type,
                    rarity=rarity,
                    host_associated=host_associated,
                    comment=comment,
                )
            )
        session.bulk_save_objects(sample_types)


def init_standard_host_species(session: sessionmaker):
    with open("standard_host_species.tsv", "r") as file:
        reader = csv.reader(file, delimiter="\t")
        next(reader)  # Skip header row
        host_species_list = []
        for row in reader:
            host_species = row[0]
            scientific_name = row[1]
            ncbi_taxon_id = row[2]
            host_species_list.append(
                StandardHostSpecies(
                    host_species=host_species,
                    scientific_name=scientific_name,
                    ncbi_taxon_id=ncbi_taxon_id,
                )
            )
        session.bulk_save_objects(host_species_list)


def query_tag_stats(db: SQLAlchemy, tag: str):
    if tag in STANDARD_TAGS.keys():
        return (
            db.session.query(
                getattr(Sample, STANDARD_TAGS[tag]).label("val"),
                db.func.count(Sample.sample_accession).label("sample_count"),
                Sample.run_accession.label("run_accession"),
                Run.run_date.label("run_date"),
                Run.comment.label("run_comment"),
            )
            .join(Run, Sample.run_accession == Run.run_accession)
            .group_by(Sample.run_accession)
            .all()
        )
    else:
        return (
            db.session.query(
                Sample.run_accession,
                Run.run_date,
                Run.comment,
                Annotation.key,
                Annotation.val,
                db.func.count(Annotation.sample_accession).label("sample_count"),
            )
            .join(Run, Sample.run_accession == Run.run_accession)
            .join(Annotation, Annotation.sample_accession == Sample.sample_accession)
            .group_by(Sample.run_accession, Annotation.key, Annotation.val)
            .order_by(
                Annotation.key,
                Run.run_date.desc(),
                Sample.run_accession,
                db.func.count(Annotation.sample_accession).desc(),
                Annotation.val,
            )
            .where(Annotation.key == tag)
            .all()
        )


def cast_annotations(
    annotations: list[Annotation], samples: list[Sample], default: str = "NA"
) -> tuple[list[str], dict]:
    cols = {}
    table = {}
    for s in samples:
        table[s.sample_accession] = {}

    for a in annotations:
        if a.key not in cols:
            # Add new column to each row of table
            for r in table.keys():
                table[r][a.key] = default
            # Add new column to future rows
            cols[a.key] = default
        table[a.sample_accession][a.key] = a.val

    return list(cols.keys()), table
