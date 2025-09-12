from typing import Optional
from sqlalchemy import and_, create_engine, delete, insert, select, update
from sqlalchemy.orm import Session, sessionmaker
from sample_registry.db import STANDARD_TAGS
from sample_registry.mapping import SampleTable
from sample_registry.models import (
    Annotation,
    Sample,
    StandardSampleType,
    StandardHostSpecies,
    Run,
)
from seqBackupLib.illumina import MACHINE_TYPES


class SampleRegistry:
    machines = MACHINE_TYPES.values()
    kits = ["Nextera XT"]

    def __init__(self, session: Optional[Session] = None, uri: Optional[str] = None):
        if session and uri:
            raise ValueError("Cannot provide both session and uri")
        elif session:
            self.session = session
        elif uri:
            engine = create_engine(uri, echo=False)
            SessionLocal = sessionmaker(bind=engine)
            self.session = SessionLocal()
        else:
            from sample_registry import session as imported_session

            self.session = imported_session

    def check_run_accession(self, acc: int) -> Run:
        run = self.session.scalar(select(Run).where(Run.run_accession == acc))
        if not run:
            raise ValueError("Run does not exist %s" % acc)
        return run

    def get_run(self, run_accession: int) -> Run | None:
        """Return the ``Run`` record for ``run_accession``.

        Parameters
        ----------
        run_accession:
            Accession number identifying the sequencing run.

        Returns
        -------
        Run | None
            The ``Run`` instance if found, otherwise ``None``.
        """

        return self.session.scalar(
            select(Run).where(Run.run_accession == run_accession)
        )

    def register_run(
        self,
        run_date: str,
        machine_type: str,
        machine_kit: str,
        lane: int,
        data_uri: str,
        comment: str,
    ) -> Optional[int]:
        # Using this because there are situations where the autoincrement is untrustworthy
        max_run_accession = self.session.scalar(
            select(Run.run_accession).order_by(Run.run_accession.desc()).limit(1)
        )

        return self.session.scalar(
            insert(Run)
            .returning(Run.run_accession)
            .values(
                {
                    "run_accession": max_run_accession + 1 if max_run_accession else 1,
                    "run_date": run_date,
                    "machine_type": machine_type,
                    "machine_kit": machine_kit,
                    "lane": lane,
                    "data_uri": data_uri,
                    "comment": comment,
                }
            )
        )

    def modify_run(self, run_accession: int, **kwargs):
        kwargs = {k: v for k, v in kwargs.items() if v is not None}
        self.session.execute(
            update(Run).where(Run.run_accession == run_accession).values(**kwargs)
        )

    def check_samples(self, run_accession: int, exists: bool = True) -> list[Sample]:
        samples = self.session.scalars(
            select(Sample).where(Sample.run_accession == run_accession)
        ).all()
        if bool(samples) != exists:
            s = "exist" if exists else "don't exist"
            raise ValueError(f"Samples {s} for run {run_accession}")
        return list(samples)

    def register_samples(
        self, run_accession: int, sample_table: SampleTable
    ) -> list[int]:
        sample_tups = [
            (sample_name, barcode_sequence)
            for sample_name, barcode_sequence in sample_table.core_info
        ]
        if self.session.scalars(
            select(Sample).where(
                and_(
                    Sample.run_accession == run_accession,
                    Sample.sample_name.in_([s[0] for s in sample_tups]),
                    Sample.barcode_sequence.in_([s[1] for s in sample_tups]),
                )
            )
        ).first():
            raise ValueError("Samples already registered for run %s" % run_accession)

        # Using this because there are situations where the autoincrement is untrustworthy
        max_sample_accession = self.session.scalar(
            select(Sample.sample_accession)
            .order_by(Sample.sample_accession.desc())
            .limit(1)
        )

        return self.session.scalars(
            insert(Sample)
            .returning(Sample.sample_accession)
            .values(
                [
                    {
                        "sample_accession": (
                            max_sample_accession + i + 1
                            if max_sample_accession
                            else i + 1
                        ),
                        "run_accession": run_accession,
                        "sample_name": sample_name,
                        "barcode_sequence": barcode_sequence,
                    }
                    for i, (sample_name, barcode_sequence) in enumerate(
                        sample_table.core_info
                    )
                ]
            )
        )

    def modify_sample(self, sample_accession: int, **kwargs):
        kwargs = {k: v for k, v in kwargs.items() if v is not None}
        self.session.execute(
            update(Sample)
            .where(Sample.sample_accession == sample_accession)
            .values(**kwargs)
        )

    def remove_samples(self, run_accession: int) -> list[int]:
        samples = self.session.scalars(
            select(Sample.sample_accession).where(Sample.run_accession == run_accession)
        ).all()
        self.session.execute(
            delete(Annotation).where(Annotation.sample_accession.in_(samples))
        )
        self.session.execute(
            delete(Sample).where(Sample.run_accession == run_accession)
        )

        return list(samples)

    def register_annotations(self, run_accession: int, sample_table: SampleTable) -> list[tuple[int, str]]:
        accessions = self._get_sample_accessions(run_accession, sample_table)

        # Remove existing annotations
        self.session.execute(
            delete(Annotation).where(Annotation.sample_accession.in_(accessions))
        )
        self.session.execute(
            update(Sample)
            .where(Sample.sample_accession.in_(accessions))
            .values({k: None for k in STANDARD_TAGS.values()})
        )

        # Register new annotations
        standard_annotation_args = []
        annotation_args = []
        for a, pairs in zip(accessions, sample_table.annotations):
            for k, v in pairs:
                if k in STANDARD_TAGS:
                    standard_annotation_args.append((a, STANDARD_TAGS[k], v))
                else:
                    annotation_args.append((a, k, v))

        for a, k, v in standard_annotation_args:
            self.session.execute(
                update(Sample).where(Sample.sample_accession == a).values({k: v})
            )

        annotation_keys = []
        if annotation_args:
            annotation_keys = self.session.scalars(
                insert(Annotation)
                .returning(Annotation.sample_accession, Annotation.key)
                .values(
                    [
                        {"sample_accession": a, "key": k, "val": v}
                        for a, k, v in annotation_args
                    ]
                )
            )

        return list(annotation_keys)

    def _get_sample_accessions(
        self, run_accession: int, sample_table: SampleTable
    ) -> list[int]:
        sample_tups = [
            (sample_name, barcode_sequence)
            for sample_name, barcode_sequence in sample_table.core_info
        ]
        accessions = self.session.scalars(
            select(Sample.sample_accession).where(
                and_(
                    Sample.run_accession == run_accession,
                    Sample.sample_name.in_([s[0] for s in sample_tups]),
                    Sample.barcode_sequence.in_([s[1] for s in sample_tups]),
                )
            )
        ).all()

        unaccessioned_recs = []
        for accession, rec in zip(accessions, sample_table.recs):
            if accession is None:
                unaccessioned_recs.append(rec)
        if unaccessioned_recs:
            raise IOError("Not accessioned: %s" % unaccessioned_recs)
        return list(accessions)

    def modify_annotation(self, sample_accession: int, key: str, val: str):
        self.session.execute(
            update(Annotation)
            .where(
                and_(
                    Annotation.sample_accession == sample_accession,
                    Annotation.key == key,
                )
            )
            .values({"val": val})
        )

    def remove_standard_sample_types(self):
        self.session.execute(delete(StandardSampleType))

    def register_standard_sample_types(
        self, sample_types: list[tuple[str, str, bool, str]]
    ):
        self.session.execute(
            insert(StandardSampleType).values(
                [
                    {
                        "sample_type": sample_type,
                        "rarity": rarity,
                        "host_associated": bool(host_associated),
                        "comment": comment,
                    }
                    for sample_type, rarity, host_associated, comment in sample_types
                ]
            )
        )

    def remove_standard_host_species(self):
        self.session.execute(delete(StandardHostSpecies))

    def register_standard_host_species(
        self, host_species
    ):
        self.session.execute(
            insert(StandardHostSpecies).values(
                [
                    {
                        "host_species": host_species,
                        "scientific_name": scientific_name,
                        "ncbi_taxon_id": int(ncbi_taxon_id),
                    }
                    for host_species, scientific_name, ncbi_taxon_id in host_species
                ]
            )
        )
