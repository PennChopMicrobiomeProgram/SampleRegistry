import csv
import pickle
import os
from collections import defaultdict
from datetime import datetime
from flask import (
    Flask,
    make_response,
    render_template,
    url_for,
    request,
    redirect,
    send_file,
    send_from_directory,
    jsonify,
)
from flask_sqlalchemy import SQLAlchemy
from contextlib import contextmanager
from io import StringIO
from pathlib import Path
from sample_registry import ARCHIVE_ROOT, SQLALCHEMY_DATABASE_URI
from sample_registry.mapping import SampleTable
from sample_registry.models import Base, Annotation, Run, Sample
from sample_registry.db import run_to_dataframe, query_tag_stats, STANDARD_TAGS
from sample_registry.registrar import SampleRegistry
from sample_registry.standards import STANDARD_HOST_SPECIES, STANDARD_SAMPLE_TYPES
from typing import Optional
from werkzeug.middleware.proxy_fix import ProxyFix
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

app = Flask(__name__)
app.secret_key = os.urandom(12)

# This line is only used in production mode on a nginx server, follow instructions to setup forwarding for
# whatever production server you are using instead. It's ok to leave this in when running the dev server.
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# Sanitize and RO db connection
SQLALCHEMY_WRITE_URI = SQLALCHEMY_DATABASE_URI
SQLALCHEMY_DATABASE_URI = f"{SQLALCHEMY_DATABASE_URI.split('?')[0]}?mode=ro"
app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
print(SQLALCHEMY_DATABASE_URI)
# Ensure SQLite explicitly opens in read-only mode
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"connect_args": {"uri": True}}
db = SQLAlchemy(model_class=Base)
db.init_app(app)
write_engine = create_engine(SQLALCHEMY_WRITE_URI, echo=False)
WriteSession = sessionmaker(bind=write_engine)


@contextmanager
def api_registry():
    session = WriteSession()
    registry = SampleRegistry(session=session)
    try:
        yield registry
    finally:
        session.close()
        registry.session.close()


def api_request_data():
    data = request.get_json(silent=True)
    if data is None:
        data = request.form.to_dict()
    return data or {}


def api_error(message: str, status: int = 400):
    return jsonify({"status": "error", "error": message}), status


def api_sample_table_from_request():
    if "sample_table" in request.files:
        content = request.files["sample_table"].stream.read().decode("utf-8")
    else:
        data = api_request_data()
        content = data.get("sample_table")
    if not content:
        raise ValueError("sample_table is required")
    sample_table = SampleTable.load(StringIO(content))
    sample_table.look_up_nextera_barcodes()
    sample_table.validate()
    return sample_table


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
def show_tags(tag: Optional[str] = None, val: Optional[str] = None):
    if val:
        if tag in STANDARD_TAGS:
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
def show_runs(run_acc: Optional[str] = None):
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
    standard_sampletypes = set(STANDARD_SAMPLE_TYPES.names())
    standard_hostspecies = set(STANDARD_HOST_SPECIES.names())

    num_samples = db.session.query(Sample).count()
    num_samples_with_sampletype = (
        db.session.query(Sample).filter(Sample.sample_type.is_not(None)).count()
    )
    num_samples_with_standard_sampletype = (
        db.session.query(Sample)
        .filter(Sample.sample_type.in_(standard_sampletypes))
        .count()
        if standard_sampletypes
        else 0
    )
    standard_sampletype_counts = (
        db.session.query(Sample.sample_type, db.func.count(Sample.sample_accession))
        .filter(Sample.sample_type.in_(standard_sampletypes))
        .group_by(Sample.sample_type)
        .order_by(db.func.count(Sample.sample_accession).desc(), Sample.sample_type)
        .all()
        if standard_sampletypes
        else []
    )
    nonstandard_sampletype_counts = (
        db.session.query(Sample.sample_type, db.func.count(Sample.sample_accession))
        .filter(
            Sample.sample_type.isnot(None),
            Sample.sample_type.notin_(standard_sampletypes),
        )
        .group_by(Sample.sample_type)
        .order_by(db.func.count(Sample.sample_accession).desc(), Sample.sample_type)
        .all()
        if standard_sampletypes
        else db.session.query(
            Sample.sample_type, db.func.count(Sample.sample_accession)
        )
        .filter(Sample.sample_type.isnot(None))
        .group_by(Sample.sample_type)
        .order_by(db.func.count(Sample.sample_accession).desc(), Sample.sample_type)
        .all()
    )

    num_subjectid = (
        db.session.query(Sample.subject_id)
        .filter(Sample.subject_id.is_not(None))
        .count()
    )
    num_subjectid_with_hostspecies = (
        db.session.query(Sample.subject_id)
        .filter(Sample.subject_id.is_not(None), Sample.host_species.is_not(None))
        .count()
    )

    num_samples_with_hostspecies = (
        db.session.query(Sample).filter(Sample.host_species.is_not(None)).count()
    )
    num_samples_with_standard_hostspecies = (
        db.session.query(Sample)
        .filter(Sample.host_species.in_(standard_hostspecies))
        .count()
        if standard_hostspecies
        else 0
    )
    standard_hostspecies_counts = (
        db.session.query(Sample.host_species, db.func.count(Sample.sample_accession))
        .filter(Sample.host_species.in_(standard_hostspecies))
        .group_by(Sample.host_species)
        .order_by(db.func.count(Sample.sample_accession).desc(), Sample.host_species)
        .all()
        if standard_hostspecies
        else []
    )
    nonstandard_hostspecies_counts = (
        db.session.query(Sample.host_species, db.func.count(Sample.sample_accession))
        .filter(
            Sample.host_species.isnot(None),
            Sample.host_species.notin_(standard_hostspecies),
        )
        .group_by(Sample.host_species)
        .order_by(db.func.count(Sample.sample_accession).desc(), Sample.host_species)
        .all()
        if standard_hostspecies
        else db.session.query(
            Sample.host_species, db.func.count(Sample.sample_accession)
        )
        .filter(Sample.host_species.isnot(None))
        .group_by(Sample.host_species)
        .order_by(db.func.count(Sample.sample_accession).desc(), Sample.host_species)
        .all()
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
def download(run_acc: str):
    ext = run_acc[-4:]
    run_acc = run_acc[:-4]
    t = run_to_dataframe(db, run_acc)
    csv_file = StringIO()
    writer = csv.writer(csv_file, delimiter="\t")

    if ext == ".txt":
        run = db.session.query(Run).filter(Run.run_accession == run_acc).first()
        if not run:
            return render_template("failed_export.html", run_acc=run_acc)

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


@app.post("/api/register_run")
def api_register_run():
    data = api_request_data()
    missing = [k for k in ("file", "date", "comment") if not data.get(k)]
    if missing:
        return api_error(f"Missing required fields: {', '.join(missing)}")
    try:
        lane = int(data.get("lane", 1))
    except ValueError as exc:
        return api_error(f"Invalid lane value: {exc}")
    with api_registry() as registry:
        try:
            run_accession = registry.register_run(
                data["date"],
                data.get("type", "Illumina-MiSeq"),
                "Nextera XT",
                lane,
                data["file"],
                data["comment"],
            )
            registry.session.commit()
        except Exception:
            registry.session.rollback()
            raise
    return jsonify({"status": "ok", "run_accession": run_accession})


def api_register_sample_annotations(register_samples: bool):
    data = api_request_data()
    if not data.get("run_accession"):
        return api_error("Missing required field: run_accession")
    try:
        run_accession = int(data["run_accession"])
    except ValueError as exc:
        return api_error(f"Invalid run_accession value: {exc}")
    try:
        sample_table = api_sample_table_from_request()
    except Exception as exc:
        return api_error(str(exc))
    with api_registry() as registry:
        try:
            if register_samples:
                registry.check_samples(run_accession, exists=False)
            registry.check_run_accession(run_accession)
            if register_samples:
                registry.register_samples(run_accession, sample_table)
            registry.register_annotations(run_accession, sample_table)
            registry.session.commit()
        except Exception:
            registry.session.rollback()
            raise
    return jsonify(
        {
            "status": "ok",
            "run_accession": run_accession,
            "sample_count": len(sample_table.recs),
        }
    )


@app.post("/api/register_samples")
def api_register_samples():
    return api_register_sample_annotations(register_samples=True)


@app.post("/api/register_annotations")
def api_register_annotations():
    return api_register_sample_annotations(register_samples=False)


@app.post("/api/unregister_samples")
def api_unregister_samples():
    data = api_request_data()
    if not data.get("run_accession"):
        return api_error("Missing required field: run_accession")
    try:
        run_accession = int(data["run_accession"])
    except ValueError as exc:
        return api_error(f"Invalid run_accession value: {exc}")
    with api_registry() as registry:
        try:
            registry.check_run_accession(run_accession)
            samples_removed = registry.remove_samples(run_accession)
            registry.session.commit()
        except Exception:
            registry.session.rollback()
            raise
    return jsonify(
        {
            "status": "ok",
            "run_accession": run_accession,
            "removed_samples": samples_removed,
        }
    )


@app.post("/api/modify_run")
def api_modify_run():
    data = api_request_data()
    if not data.get("run_accession"):
        return api_error("Missing required field: run_accession")
    try:
        run_accession = int(data["run_accession"])
    except ValueError as exc:
        return api_error(f"Invalid run_accession value: {exc}")
    lane = data.get("lane")
    if lane is not None:
        try:
            lane = int(lane)
        except ValueError as exc:
            return api_error(f"Invalid lane value: {exc}")
    with api_registry() as registry:
        try:
            registry.check_run_accession(run_accession)
            registry.modify_run(
                run_accession=run_accession,
                run_date=data.get("date"),
                machine_type=data.get("type"),
                machine_kit=data.get("kit"),
                lane=lane,
                data_uri=data.get("data_uri"),
                comment=data.get("comment"),
                admin_comment=data.get("admin_comment"),
            )
            registry.session.commit()
        except Exception:
            registry.session.rollback()
            raise
    return jsonify({"status": "ok", "run_accession": run_accession})


@app.post("/api/modify_sample")
def api_modify_sample():
    data = api_request_data()
    if not data.get("sample_accession"):
        return api_error("Missing required field: sample_accession")
    try:
        sample_accession = int(data["sample_accession"])
    except ValueError as exc:
        return api_error(f"Invalid sample_accession value: {exc}")
    with api_registry() as registry:
        try:
            registry.check_sample_accession(sample_accession)
            registry.modify_sample(
                sample_accession=sample_accession,
                sample_name=data.get("sample_name"),
                sample_type=data.get("sample_type"),
                subject_id=data.get("subject_id"),
                host_species=data.get("host_species"),
                barcode_sequence=data.get("barcode_sequence"),
                primer_sequence=data.get("primer_sequence"),
            )
            registry.session.commit()
        except Exception:
            registry.session.rollback()
            raise
    return jsonify({"status": "ok", "sample_accession": sample_accession})


@app.post("/api/modify_annotation")
def api_modify_annotation():
    data = api_request_data()
    missing = [k for k in ("sample_accession", "key", "val") if not data.get(k)]
    if missing:
        return api_error(f"Missing required fields: {', '.join(missing)}")
    try:
        sample_accession = int(data["sample_accession"])
    except ValueError as exc:
        return api_error(f"Invalid sample_accession value: {exc}")
    with api_registry() as registry:
        try:
            registry.check_sample_accession(sample_accession)
            registry.modify_annotation(
                sample_accession=sample_accession,
                key=data["key"],
                val=data["val"],
            )
            registry.session.commit()
        except Exception:
            registry.session.rollback()
            raise
    return jsonify({"status": "ok", "sample_accession": sample_accession})


@app.route("/description")
def show_description():
    return render_template("description.html")


@app.route("/")
def index():
    return redirect(url_for("show_runs"))


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=80)
