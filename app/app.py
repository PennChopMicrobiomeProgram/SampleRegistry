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
from sample_registry.models import Base, Annotation, Run, Sample
from werkzeug.middleware.proxy_fix import ProxyFix
from .db import query_tag_stats, STANDARD_TAGS

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
def show_tags(tag = None, val = None):
    if val:
        if tag in STANDARD_TAGS.keys():
            samples = db.session.query(Sample.sample_accession, Sample.sample_name, Sample.primer_sequence, Run.run_accession, Run.run_date).join(Run, Sample.run_accession == Run.run_accession).filter(getattr(Sample, STANDARD_TAGS[tag]) == val).all()
            print(samples)
        else:
            annotations = db.session.query(Annotation).filter(Annotation.key == tag, Annotation.val == val).all()
            sample_accessions = [a.sample_accession for a in annotations]
            samples = db.session.query(Sample.sample_accession, Sample.sample_name, Sample.primer_sequence, Run.run_accession, Run.run_date).join(Run, Sample.run_accession == Run.run_accession).filter(Sample.sample_accession.in_(sample_accessions)).order_by(Run.run_date.desc(), Run.machine_type, Run.machine_kit, Run.lane, Sample.sample_accession).all()
            print

        sample_annotations = db.session.query(Annotation).filter(Annotation.sample_accession.in_([s.sample_accession for s in samples])).all()
        keyed_metadata = {sa: [a for a in sample_annotations if a.sample_accession == sa] for sa in [s.sample_accession for s in samples]}

        return render_template("show_tag_value.html", tag=tag, val=val, samples=samples, sample_metadata=keyed_metadata)
    elif tag:
        stats = query_tag_stats(db, tag)
        return render_template("show_tag.html", tag=tag, stats=stats)
    else:
        tags = db.session.query(Annotation.key, db.func.count(Annotation.key)).group_by(Annotation.key).all()
        return render_template("browse_tags.html", tags=tags, maxcnt=max([t[1] for t in tags]))


@app.route("/runs")
@app.route("/runs/<run_acc>")
def show_runs(run_acc = None):
    if request.path.endswith(".json"):
        run = db.session.query(Run).filter(Run.run_accession == run_acc).all()
        with open(f"run_{run_acc}", "wb") as f: # TEMP
            pickle.dump(run, f)
        return send_file(f"run_{run_acc}", as_attachment=True)
    elif request.path.endswith(".txt"):
        run = db.session.query(Run).filter(Run.run_accession == run_acc).all()
        with open(f"run_{run_acc}", "wb") as f: # TEMP
            pickle.dump(run, f)
        return send_file(f"run_{run_acc}", as_attachment=True)
    elif request.path.endswith(".tsv"):
        run = db.session.query(Run).filter(Run.run_accession == run_acc).all()
        with open(f"run_{run_acc}", "wb") as f: # TEMP
            pickle.dump(run, f)
        return send_file(f"run_{run_acc}", as_attachment=True)
    elif run_acc:
        run = db.session.query(Run).filter(Run.run_accession == run_acc).all()
        samples = db.session.query(Sample).filter(Sample.run_accession == run_acc).order_by(Sample.sample_name, Sample.sample_accession).all()
        annotations = db.session.query(Annotation).filter(Annotation.sample_accession.in_([s.sample_accession for s in samples])).all()
        keyed_annotations = {sa: [a for a in annotations if a.sample_accession == sa] for sa in [s.sample_accession for s in samples]}

        return render_template("show_run.html", run=run, samples=samples, sample_metadata=keyed_annotations)
    else:
        runs = db.session.query(Run).all()
        return render_template("browse_runs.html", runs=runs)
    

@app.route("/stats")
def show_stats():
    return render_template("show_stats.html")


@app.route("/")
def index():
    return redirect(url_for("show_runs"))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)