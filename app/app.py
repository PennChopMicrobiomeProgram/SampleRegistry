import os
from flask import (
    Flask,
    render_template,
    url_for,
    request,
    redirect,
    flash,
    send_from_directory,
)
from app.sample_registry.src.models import Annotation
from flask_sqlalchemy import SQLAlchemy
from pathlib import Path
from sample_registry.src import SQLALCHEMY_DATABASE_URI
from sample_registry.src.models import Base
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
app.secret_key = os.urandom(12)

# This line is only used in production mode on a nginx server, follow instructions to setup forwarding for
# whatever production server you are using instead. It's ok to leave this in when running the dev server.
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
db = SQLAlchemy(model_class=Base)
db.init_app(app)

@app.route("/favicon.ico")
def favicon():
    return send_from_directory(
        Path(app.root_path) / "static" / "img",
        "favicon.ico",
        mimetype="image/vnd.microsoft.icon",
    )


@app.route("/tags")
def show_tags():
    tags = db.session.query(Annotation.key, db.func.count(Annotation.key)).group_by(Annotation.key).all()
    maxcnt = 0
    for t in tags:
        if t.key_counts > maxcnt:
            maxcnt = t.key_counts
    return render_template("browse_tags.html", tags=tags, maxcnt=maxcnt)


@app.route("/")
def index():
    return render_template("index.html")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)