import pickle
import os
from flask import (
    Flask,
    render_template,
    url_for,
    request,
    redirect,
    send_file,
    send_from_directory,
)
from flask_sqlalchemy import SQLAlchemy
from pathlib import Path
from sample_registry import SQLALCHEMY_DATABASE_URI
from sample_registry.models import (
    Base,
    Annotation,
    Run,
    Sample,
    StandardHostSpecies,
    StandardSampleType,
)
from sample_registry.db import cast_annotations, query_tag_stats, STANDARD_TAGS
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
app.secret_key = os.urandom(12)

# This line is only used in production mode on a nginx server, follow instructions to setup forwarding for
# whatever production server you are using instead. It's ok to leave this in when running the dev server.
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
print(SQLALCHEMY_DATABASE_URI)
db = SQLAlchemy(model_class=Base)
db.init_app(app)

with app.app_context():
    db.create_all()


@app.route("/favicon.ico")
def favicon():
    return send_from_directory(
        Path(app.root_path) / "static" / "img",
        "favicon.ico",
        mimetype="image/vnd.microsoft.icon",
    )


@app.route("/tags")
@app.route("/tags/<tag>")
@app.route("/tags/<tag>/<val>")
def show_tags(tag=None, val=None):
    if val:
        if tag in STANDARD_TAGS.keys():
            samples = (
                db.session.query(
                    Sample.sample_accession,
                    Sample.sample_name,
                    Sample.primer_sequence,
                    Run.run_accession,
                    Run.run_date,
                )
                .join(Run, Sample.run_accession == Run.run_accession)
                .filter(getattr(Sample, STANDARD_TAGS[tag]) == val)
                .all()
            )
        else:
            annotations = (
                db.session.query(Annotation)
                .filter(Annotation.key == tag, Annotation.val == val)
                .all()
            )
            sample_accessions = [a.sample_accession for a in annotations]
            samples = (
                db.session.query(
                    Sample.sample_accession,
                    Sample.sample_name,
                    Sample.primer_sequence,
                    Run.run_accession,
                    Run.run_date,
                )
                .join(Run, Sample.run_accession == Run.run_accession)
                .filter(Sample.sample_accession.in_(sample_accessions))
                .order_by(
                    Run.run_date.desc(),
                    Run.machine_type,
                    Run.machine_kit,
                    Run.lane,
                    Sample.sample_accession,
                )
                .all()
            )

        sample_annotations = (
            db.session.query(Annotation)
            .filter(
                Annotation.sample_accession.in_([s.sample_accession for s in samples])
            )
            .all()
        )
        keyed_metadata = {
            sa: [a for a in sample_annotations if a.sample_accession == sa]
            for sa in [s.sample_accession for s in samples]
        }

        return render_template(
            "show_tag_value.html",
            tag=tag,
            val=val,
            samples=samples,
            sample_metadata=keyed_metadata,
        )
    elif tag:
        stats = query_tag_stats(db, tag)
        return render_template("show_tag.html", tag=tag, stats=stats)
    else:
        tags = (
            db.session.query(Annotation.key, db.func.count(Annotation.key))
            .group_by(Annotation.key)
            .all()
        )
        maxcnt = max([t[1] for t in tags]) if tags else 0
        return render_template("browse_tags.html", tags=tags, maxcnt=maxcnt)


@app.route("/runs")
@app.route("/runs/<run_acc>")
def show_runs(run_acc=None):
    if run_acc:
        run_acc = "".join(filter(str.isdigit, run_acc.strip()))  # Sanitize run_acc

    if request.path.endswith(".json"):
        run = db.session.query(Run).filter(Run.run_accession == run_acc).all()
        with open(f"run_{run_acc}", "wb") as f:  # TEMP
            pickle.dump(run, f)
        return send_file(f"run_{run_acc}", as_attachment=True)
    elif request.path.endswith(".txt"):
        run = db.session.query(Run).filter(Run.run_accession == run_acc).all()
        with open(f"run_{run_acc}", "wb") as f:  # TEMP
            pickle.dump(run, f)
        return send_file(f"run_{run_acc}", as_attachment=True)
    elif request.path.endswith(".tsv"):
        run = db.session.query(Run).filter(Run.run_accession == run_acc).all()
        with open(f"run_{run_acc}", "wb") as f:  # TEMP
            pickle.dump(run, f)
        return send_file(f"run_{run_acc}", as_attachment=True)
    elif run_acc:
        run = db.session.query(Run).filter(Run.run_accession == run_acc).all()
        samples = (
            db.session.query(Sample)
            .filter(Sample.run_accession == run_acc)
            .order_by(Sample.sample_name, Sample.sample_accession)
            .all()
        )
        annotations = (
            db.session.query(Annotation)
            .filter(
                Annotation.sample_accession.in_([s.sample_accession for s in samples])
            )
            .all()
        )
        keyed_annotations = {
            sa: [a for a in annotations if a.sample_accession == sa]
            for sa in [s.sample_accession for s in samples]
        }

        return render_template(
            "show_run.html", run=run, samples=samples, sample_metadata=keyed_annotations
        )
    else:
        runs = db.session.query(Run).all()[::-1]
        sample_counts = {
            r: db.session.query(Sample)
            .filter(Sample.run_accession == r.run_accession)
            .count()
            for r in runs
        }
        return render_template("browse_runs.html", runs=runs)


@app.route("/stats")
def show_stats():
    num_samples = db.session.query(Sample).count()
    num_samples_with_sampletype = (
        db.session.query(Sample).filter(Sample.sample_type is not None).count()
    )
    num_samples_with_standard_sampletype = (
        db.session.query(Sample)
        .join(StandardSampleType, Sample.sample_type == StandardSampleType.sample_type)
        .count()
    )
    standard_sampletype_counts = (
        db.session.query(
            StandardSampleType.sample_type,
            db.func.count(Sample.sample_accession),
            StandardSampleType.host_associated,
        )
        .join(Sample, Sample.sample_type == StandardSampleType.sample_type)
        .group_by(StandardSampleType.sample_type)
        .order_by(db.func.count(Sample.sample_accession).desc())
        .all()
    )
    standard_sampletypes = set(
        s.sample_type for s in db.session.query(StandardSampleType.sample_type).all()
    )
    nonstandard_sampletype_counts = (
        db.session.query(Sample.sample_type, db.func.count(Sample.sample_accession))
        .filter(Sample.sample_type.notin_(standard_sampletypes))
        .order_by(db.func.count(Sample.sample_accession).desc())
    )

    num_subjectid = (
        db.session.query(Sample.subject_id)
        .filter(Sample.subject_id is not None)
        .count()
    )
    num_subjectid_with_hostspecies = (
        db.session.query(Sample.subject_id)
        .filter(Sample.subject_id is not None, Sample.host_species is not None)
        .count()
    )

    num_samples_with_hostspecies = (
        db.session.query(Sample).filter(Sample.host_species is not None).count()
    )
    num_samples_with_standard_hostspecies = (
        db.session.query(Sample)
        .join(
            StandardHostSpecies, Sample.host_species == StandardHostSpecies.host_species
        )
        .count()
    )
    standard_hostspecies_counts = (
        db.session.query(
            StandardHostSpecies.host_species,
            db.func.count(Sample.sample_accession),
            StandardHostSpecies.ncbi_taxon_id,
        )
        .join(Sample, Sample.host_species == StandardHostSpecies.host_species)
        .group_by(StandardHostSpecies.host_species)
        .order_by(db.func.count(Sample.sample_accession).desc())
        .all()
    )
    standard_hostspecies = set(
        s.host_species for s in db.session.query(StandardHostSpecies.host_species).all()
    )
    nonstandard_hostspecies_counts = (
        db.session.query(Sample.host_species, db.func.count(Sample.sample_accession))
        .filter(Sample.host_species.notin_(standard_hostspecies))
        .order_by(db.func.count(Sample.sample_accession).desc())
    )

    num_samples_with_primer = (
        db.session.query(Sample).filter(Sample.primer_sequence != "").count()
    )
    num_samples_with_reverse_primer = (
        db.session.query(Annotation)
        .filter(Annotation.key == "ReversePrimerSequence")
        .distinct()
        .count()
    )

    return render_template(
        "show_stats.html",
        num_samples=num_samples,
        num_samples_with_sampletype=num_samples_with_sampletype,
        num_samples_with_standard_sampletype=num_samples_with_standard_sampletype,
        standard_sampletype_counts=standard_sampletype_counts,
        nonstandard_sampletype_counts=nonstandard_sampletype_counts,
        num_subjectid=num_subjectid,
        num_subjectid_with_hostspecies=num_subjectid_with_hostspecies,
        num_samples_with_hostspecies=num_samples_with_hostspecies,
        num_samples_with_standard_hostspecies=num_samples_with_standard_hostspecies,
        standard_hostspecies_counts=standard_hostspecies_counts,
        nonstandard_hostspecies_counts=nonstandard_hostspecies_counts,
        num_samples_with_primer=num_samples_with_primer,
        num_samples_with_reverse_primer=num_samples_with_reverse_primer,
    )


@app.route("/export/<run_acc>")
def export_run(run_acc):
    if run_acc.endswith(".txt"):
        run_acc = run_acc[:-4]
        run = db.session.query(Run).filter(Run.run_accession == run_acc).first()
        samples = (
            db.session.query(Sample)
            .filter(Sample.run_accession == run_acc)
            .order_by(Sample.sample_name, Sample.sample_accession)
            .all()
        )
        annotations = (
            db.session.query(Annotation)
            .filter(
                Annotation.sample_accession.in_([s.sample_accession for s in samples])
            )
            .all()
        )

        # Change ReversePrimerSequence for compatibility with QIIME
        for a in annotations:
            if a.key == "ReversePrimerSequence":
                a.key = "ReversePrimer"

        cols, table = cast_annotations(annotations, samples)

        return render_template(
            "export_qiime.txt",
            run=run,
            samples=samples,
            metadata=table,
            metadata_columns=cols,
        )
    elif run_acc.endswith(".tsv"):
        run_acc = run_acc[:-4]
        run = db.session.query(Run).filter(Run.run_accession == run_acc).first()
        samples = (
            db.session.query(Sample)
            .filter(Sample.run_accession == run_acc)
            .order_by(Sample.sample_name, Sample.sample_accession)
            .all()
        )
        annotations = (
            db.session.query(Annotation)
            .filter(
                Annotation.sample_accession.in_([s.sample_accession for s in samples])
            )
            .all()
        )
        cols, table = cast_annotations(annotations, samples)

        return render_template(
            "export_delim.txt",
            run=run,
            samples=samples,
            metadata=table,
            metadata_columns=cols,
        )
    else:
        return render_template("failed_export.html", run_acc=run_acc)


@app.route("/")
def index():
    return redirect(url_for("show_runs"))


if __name__ == "__main__":
    # port = int(os.environ.get("PORT", 80))
    app.run(host="0.0.0.0", port=80)
