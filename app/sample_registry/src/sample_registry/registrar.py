from sqlalchemy import and_, delete, insert, select, update
from sqlalchemy.orm import Session
from sample_registry.db import STANDARD_TAGS
from sample_registry.mapping import SampleTable
from sample_registry.models import (
    Annotation,
    Sample,
    StandardSampleType,
    StandardHostSpecies,
    Run,
)


class SampleRegistry(object):
    machines = [
        "Illumina-MiSeq",
        "Illumina-HiSeq",
        "Illumina-NovaSeq",
        "Illumina-MiniSeq",
    ]
    kits = ["Nextera XT"]

    def __init__(self, session: Session = None):
        if session:
            self.session = session
        else:
            from sample_registry import session as imported_session

            self.session = imported_session

    def check_run_accession(self, acc: int) -> Run:
        run = self.session.scalar(select(Run).where(Run.run_accession == acc))
        if not run:
            raise ValueError("Run does not exist %s" % acc)
        return run

    def register_run(
        self,
        run_date: str,
        machine_type: str,
        machine_kit: str,
        lane: int,
        data_uri: str,
        comment: str,
    ) -> int:
        run_acc = self.session.scalar(
            insert(Run)
            .returning(Run.run_accession)
            .values(
                {
                    "run_date": run_date,
                    "machine_type": machine_type,
                    "machine_kit": machine_kit,
                    "lane": lane,
                    "data_uri": data_uri,
                    "comment": comment,
                }
            )
        )

        self.session.commit()
        return run_acc

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

        sample_accs = self.session.scalars(
            insert(Sample)
            .returning(Sample.sample_accession)
            .values(
                [
                    {
                        "run_accession": run_accession,
                        "sample_name": sample_name,
                        "barcode_sequence": barcode_sequence,
                    }
                    for sample_name, barcode_sequence in sample_table.core_info
                ]
            )
        )

        self.session.commit()
        return sample_accs

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

        self.session.commit()
        return samples

    def register_annotations(self, run_accession: int, sample_table: SampleTable):
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

        self.session.commit()
        return annotation_keys

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
        return accessions

    def remove_standard_sample_types(self):
        self.session.execute(delete(StandardSampleType))
        self.session.commit()

    def register_standard_sample_types(self, sample_types: list[tuple[str, str, bool]]):
        self.session.execute(
            insert(StandardSampleType).values(
                [
                    {
                        "sample_type": sample_type,
                        "rarity": rarity,
                        "host_associated": bool(host_associated),
                    }
                    for sample_type, rarity, host_associated in sample_types
                ]
            )
        )

        self.session.commit()

    def remove_standard_host_species(self):
        self.session.execute(delete(StandardHostSpecies))
        self.session.commit()

    def register_standard_host_species(
        self, host_species
    ) -> list[tuple[str, str, int]]:
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

        self.session.commit()
