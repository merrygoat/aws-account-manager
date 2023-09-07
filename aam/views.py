import flask
from flask import render_template, request

from aam import app
import aam.queries.organization

def html_response(response) -> flask.Response:
    return flask.make_response((response, 200, {'Content-Type': 'text/html; charset=utf-8'}))


@app.route('/', methods=["GET"])
def index() -> flask.Response:
    return html_response(render_template("index.html"))


@app.route('/organization', methods=["GET"])
def organization() -> flask.Response:
    return html_response(render_template("organization.html"))


@app.route('/organization/data', methods=["GET", "POST"])
def get_organizations() -> flask.Response:
    if request.method == "GET":
        all_organizations = aam.queries.organization.get_all_organizations()
        return flask.make_response(all_organizations, 200, {'Content-Type': 'text/json; charset=utf-8'})
    elif request.method == "POST":
        result = aam.queries.organization.add_new_organization(request.json)
        if result.success:
            return flask.make_response(result.response, 200, {'Content-Type': 'text/html; charset=utf-8'})


@app.route('/organization/data/<record_id>', methods=["DELETE", "PUT"])
def delete_organization(record_id: str) -> flask.Response:
    record_id = int(record_id)
    if request.method == "DELETE":
        result = aam.queries.organization.delete_organization(record_id)
        if result.success:
            return flask.make_response("", 200)
    elif request.method == "PUT":
        result = aam.queries.organization.edit_organization(record_id, request.json)
        if result.success:
            return flask.make_response("", 200)

