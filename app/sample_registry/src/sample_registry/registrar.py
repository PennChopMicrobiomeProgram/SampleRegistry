from sample_registry import session
from sqlalchemy import insert, select
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

    def remove_samples(self, run_accession):
        accessions = self.db.query_sample_accessions(run_accession)
        self.db.remove_annotations(accessions)
        self.db.remove_samples(accessions)
        return accessions

    def register_annotations(self, run_accession, sample_table):
        accessions = self._get_sample_accessions(run_accession, sample_table)
        annotation_args = []
        for a, pairs in zip(accessions, sample_table.annotations):
            for k, v in pairs:
                annotation_args.append((a, k, v))
        self.db.remove_annotations(accessions)
        self.db.register_annotations(annotation_args)

    def _get_sample_accessions(self, run_accession, sample_table):
        args = [(run_accession, n, b) for n, b in sample_table.core_info]
        accessions = self.db.query_barcoded_sample_accessions(
            run_accession, sample_table.core_info
        )
        unaccessioned_recs = []
        for accession, rec in zip(accessions, sample_table.recs):
            if accession is None:
                unaccessioned_recs.append(rec)
        if unaccessioned_recs:
            raise IOError("Not accessioned: %s" % unaccessioned_recs)
        return accessions
