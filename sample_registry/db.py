import csv
import sys
from typing import Optional
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import sessionmaker
from sample_registry import NULL_VALUES
from sample_registry.models import (
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


def create_test_db(session: Optional[sessionmaker] = None):
    if not session:
        from sample_registry import engine
        from sample_registry import session as imported_session

        session = imported_session
        Base.metadata.create_all(engine)

    if session.query(Run).count() > 0:
        sys.stderr.write(
            "Database already contains data, please delete any existing test database before running this command"
        )
        sys.exit(1)

    run1 = Run(
        run_accession=1,
        run_date="2024-07-02",
        machine_type="Illumina-NovaSeq",
        machine_kit="Nextera XT",
        lane=2,
        data_uri="raw_data/run1/Undetermined_S0_L002_R1_001.fastq.gz",
        comment="Test run 1",
    )
    run2 = Run(
        run_accession=2,
        run_date="2024-06-27",
        machine_type="Illumina-Novaseq",
        machine_kit="MiSeq Reagent Kit v3",
        lane=4,
        data_uri="raw_data/run2/Undetermined_S0_L004_R1_001.fastq.gz",
        comment="Test run 2",
    )
    run3 = Run(
        run_accession=3,
        run_date="2024-06-27",
        machine_type="Illumina-Novaseq",
        machine_kit="MiSeq Reagent Kit v3",
        lane=1,
        data_uri="raw_data/run3/Undetermined_S0_L001_R1_001.fastq.gz",
        comment="Test run 3 (NO SAMPLES)",
    )
    session.bulk_save_objects([run1, run2, run3])

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
    sample5 = Sample(
        sample_accession=5,
        sample_name="Sample5",
        run_accession=run2.run_accession,
        barcode_sequence="TTTT",
        primer_sequence="AAAA",
        sample_type="Non-Standard Sample Type",
        subject_id="Subject5",
        host_species="Non-Standard Host Species",
    )
    session.bulk_save_objects([sample1, sample2, sample3, sample4, sample5])

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


def query_tag_stats(db: SQLAlchemy, tag: str) -> list[dict]:
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
            .group_by(
                Sample.run_accession,
                getattr(Sample, STANDARD_TAGS[tag]),
                Run.run_date,
                Run.comment,
            )
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
            .group_by(
                Sample.run_accession,
                Annotation.key,
                Annotation.val,
                Run.run_date,
                Run.comment,
            )
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


def run_to_dataframe(db: SQLAlchemy, run_acc: str) -> dict[str, str]:
    run = db.session.query(Run).filter(Run.run_accession == run_acc).first()
    if not run:
        return {}

    samples = (
        db.session.query(Sample).filter(Sample.run_accession == run.run_accession).all()
    )
    annotations = (
        db.session.query(Annotation)
        .filter(Annotation.sample_accession.in_([s.sample_accession for s in samples]))
        .all()
    )

    col_names = [
        "sample_name",
        "barcode_sequence",
        "primer_sequence",
        "sample_type",
        "subject_id",
        "host_species",
    ]
    for a in annotations:
        if a.key not in col_names:
            col_names.append(a.key)
    col_names.append("sample_accession")
    table = {cn: [] for cn in col_names}

    for s in samples:
        table["sample_name"].append(s.sample_name)
        (
            table["barcode_sequence"].append(s.barcode_sequence)
            if s.barcode_sequence
            else None
        )
        (
            table["primer_sequence"].append(s.primer_sequence)
            if s.primer_sequence
            else None
        )
        table["sample_type"].append(s.sample_type) if s.sample_type else None
        table["subject_id"].append(s.subject_id) if s.subject_id else None
        table["host_species"].append(s.host_species) if s.host_species else None
        for a in (a for a in annotations if a.sample_accession == s.sample_accession):
            table[a.key].append(a.val)
        table["sample_accession"].append("CMS{:06d}".format(s.sample_accession))

        # Fill in missing values as NA
        l = len(table["sample_accession"])
        for k in col_names:
            if len(table[k]) < l:
                table[k].append("NA")
            if table[k][-1] in NULL_VALUES:
                table[k][-1] = "NA"

    # Convert table keys according to REPLACEMENTS map
    REPLACEMENTS = {
        "SampleID": "sample_name",
        "SampleType": "sample_type",
        "SubjectID": "subject_id",
        "HostSpecies": "host_species",
        "Barcode": "barcode_sequence",
        "Primer": "primer_sequence",
    }
    table = {
        {v: k for k, v in REPLACEMENTS.items()}.get(k, k): v for k, v in table.items()
    }

    return table


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
