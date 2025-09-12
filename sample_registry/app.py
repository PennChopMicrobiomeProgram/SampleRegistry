import csv
import pickle
import os
from flask import (
    Flask,
    make_response,
    render_template,
    url_for,
    request,
    redirect,
    send_file,
    send_from_directory,
)
from flask_sqlalchemy import SQLAlchemy
from io import StringIO
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
from sample_registry.db import run_to_dataframe, query_tag_stats, STANDARD_TAGS
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
        Path(app.root_path) / "static",
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
            d[0]: d[1]
            for d in db.session.query(
                Sample.run_accession, db.func.count(Sample.sample_accession)
            )
            .group_by(Sample.run_accession)
            .all()
        }
        sample_counts = {run: sample_counts.get(run.run_accession, 0) for run in runs}
        return render_template("browse_runs.html", sample_counts=sample_counts)


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
        .order_by(
            db.func.count(Sample.sample_accession).desc(),
            StandardSampleType.sample_type,
        )
        .all()
    )
    standard_sampletypes = set(
        s.sample_type for s in db.session.query(StandardSampleType.sample_type).all()
    )
    nonstandard_sampletype_counts = (
        db.session.query(Sample.sample_type, db.func.count(Sample.sample_accession))
        .filter(Sample.sample_type.notin_(standard_sampletypes))
        .group_by(Sample.sample_type)
        .order_by(db.func.count(Sample.sample_accession).desc(), Sample.sample_type)
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
        .order_by(
            db.func.count(Sample.sample_accession).desc(),
            StandardHostSpecies.host_species,
        )
        .all()
    )
    standard_hostspecies = set(
        s.host_species for s in db.session.query(StandardHostSpecies.host_species).all()
    )
    nonstandard_hostspecies_counts = (
        db.session.query(Sample.host_species, db.func.count(Sample.sample_accession))
        .filter(Sample.host_species.notin_(standard_hostspecies))
        .group_by(Sample.host_species)
        .order_by(db.func.count(Sample.sample_accession).desc(), Sample.host_species)
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


@app.route("/download/<run_acc>", methods=["GET", "POST"])
def download(run_acc):
    ext = run_acc[-4:]
    run_acc = run_acc[:-4]
    t = run_to_dataframe(db, run_acc)
    csv_file = StringIO()
    writer = csv.writer(csv_file, delimiter="\t")

    if ext == ".txt":
        run = db.session.query(Run).filter(Run.run_accession == run_acc).first()
        QIIME_HEADERS = {
            "Barcode": "BarcodeSequence",
            "Primer": "LinkerPrimerSequence",
            "sample_accession": "Description",
        }
        t = {QIIME_HEADERS.get(k, k): v for k, v in t.items()}
        commented_headers = [f"#{list(t.keys())[0]}"] + list(t.keys())[1:]
        writer.writerow(commented_headers)
        writer.writerow([f"#{run.comment.strip()}"])
        writer.writerow([f"#Sequencing date: {run.run_date}"])
        writer.writerow([f"#File name: {run.data_uri.split('/')[-1]}"])
        writer.writerow([f"#Lane: {run.lane}"])
        writer.writerow([f"#Platform: {run.machine_type} {run.machine_kit}"])
        writer.writerow([f"#Run accession: CMR{run.run_accession:06d}"])
        for row in zip(*t.values()):
            writer.writerow(row)
    elif ext == ".tsv":
        writer.writerow(t.keys())
        for row in zip(*t.values()):
            writer.writerow(row)
    else:
        return render_template("failed_export.html", run_acc=run_acc)

    # Create the response and set the appropriate headers
    response = make_response(csv_file.getvalue())
    response.headers["Content-Disposition"] = f"attachment; filename={run_acc}{ext}"
    response.headers["Content-type"] = "text/csv"
    return response


@app.route("/description")
def show_description():
    return render_template("description.html")


@app.route("/")
def index():
    return redirect(url_for("show_runs"))


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=80)
