# All Flask SQLAlchemy code, non-Flask code is in sample_registry
from flask_sqlalchemy import SQLAlchemy
from sample_registry.models import Sample, Run, Annotation

STANDARD_TAGS = {
    "SampleType": "sample_type",
    "SubjectID": "subject_id",
    "HostSpecies": "host_species",
}


def query_tag_stats(db: SQLAlchemy, tag: str):
    if tag in STANDARD_TAGS.keys():
        return db.session.query(
            getattr(Sample, STANDARD_TAGS[tag]).label('val'),
            db.func.count(Sample.sample_accession).label('sample_count'),
            Sample.run_accession.label('run_accession'),
            Run.run_date.label('run_date'),
            Run.comment.label('run_comment')
        ).join(Run, Sample.run_accession == Run.run_accession
        ).group_by(Sample.run_accession
        ).all()
    else:
        return db.session.query(
            Sample.run_accession,
            Run.run_date,
            Run.comment,
            Annotation.key,
            Annotation.val,
            db.func.count(Annotation.sample_accession).label('sample_count')
        ).join(Run, Sample.run_accession == Run.run_accession
        ).join(Annotation, Annotation.sample_accession == Sample.sample_accession
        ).group_by(
            Sample.run_accession,
            Annotation.key,
            Annotation.val
        ).order_by(
            Annotation.key,
            Run.run_date.desc(),
            Sample.run_accession,
            db.func.count(Annotation.sample_accession).desc(),
            Annotation.val
        ).where(Annotation.key == tag
        ).all()
    
def cast_annotations(annotations, samples, default="NA"):
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