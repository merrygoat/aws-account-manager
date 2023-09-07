import flask
from flask import render_template

from aam import app


def html_response(response) -> flask.Response:
    return flask.make_response((response, 200, {'Content-Type': 'text/html; charset=utf-8'}))


@app.route('/', methods=["GET"])
def index() -> flask.Response:
    return html_response(render_template("index.html"))


@app.route('/about', methods=["GET"])
def about() -> flask.Response:
    return html_response(render_template("about.html"))
