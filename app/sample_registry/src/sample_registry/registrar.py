from sample_registry import session
from sqlalchemy import delete, insert, select, update
from sample_registry.db import STANDARD_TAGS
from sample_registry.mapping import SampleTable
from sample_registry.models import Annotation, Sample, Run


class SampleRegistry(object):
    machines = [
        "Illumina-MiSeq",
        "Illumina-HiSeq",
        "Illumina-NovaSeq",
        "Illumina-MiniSeq",
    ]
    kits = ["Nextera XT"]

    def check_run_accession(self, acc: int) -> Run:
        runs = session.scalars(select(Run).where(Run.run_accession == acc))
        if len(runs) == 0:
            raise ValueError("Run does not exist %s" % acc)
        return runs[0]

    def register_samples(
        self, run_accession: int, sample_table: SampleTable
    ) -> list[Sample]:
        sample_tups = [
            (sample_name, barcode_sequence)
            for sample_name, barcode_sequence in sample_table.core_info
        ]
        if session.scalars(
            select(Sample).where(
                Sample.run_accession == run_accession
                and Sample.sample_name.in_([s[0] for s in sample_tups])
                and Sample.barcode_sequence.in_([s[1] for s in sample_tups])
            )
        ):
            raise ValueError("Samples already registered for run %s" % run_accession)

        return session.scalars(
            insert(Sample).returning(Sample),
            [
                {
                    "run_accession": run_accession,
                    "sample_name": sample_name,
                    "barcode_sequence": barcode_sequence,
                }
                for sample_name, barcode_sequence in sample_table.core_info
            ],
        )

    def remove_samples(self, run_accession: int) -> list[int]:
        samples = session.scalars(
            select(Sample.sample_accession).where(Sample.run_accession == run_accession)
        )
        session.execute(
            delete(Annotation).where(Annotation.sample_accession.in_(samples))
        )
        session.execute(delete(Sample).where(Sample.run_accession == run_accession))
        return samples

    def register_annotations(self, run_accession, sample_table):
        accessions = self._get_sample_accessions(run_accession, sample_table)

        # Remove existing annotations
        session.execute(
            delete(Annotation).where(Annotation.sample_accession.in_(accessions))
        )
        session.execute(
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
            session.execute(update(Sample).where(Sample.sample_accession == a)).values(
                {k: v}
            )
        session.execute(insert(Annotation), annotation_args)

    def _get_sample_accessions(self, run_accession, sample_table):
        sample_tups = [
            (sample_name, barcode_sequence)
            for sample_name, barcode_sequence in sample_table.core_info
        ]
        accessions = select(Sample).where(
            Sample.run_accession == run_accession
            and Sample.sample_name.in_([s[0] for s in sample_tups])
            and Sample.barcode_sequence.in_([s[1] for s in sample_tups])
        )

        unaccessioned_recs = []
        for accession, rec in zip(accessions, sample_table.recs):
            if accession is None:
                unaccessioned_recs.append(rec)
        if unaccessioned_recs:
            raise IOError("Not accessioned: %s" % unaccessioned_recs)
        return accessions
