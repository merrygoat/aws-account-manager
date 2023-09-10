import flask
from flask import render_template, request

from aam import app
import aam.queries.organization
import aam.queries.account


def html_response(response) -> flask.Response:
    return flask.make_response((response, 200, {'Content-Type': 'text/html; charset=utf-8'}))


@app.route('/', methods=["GET"])
def index() -> flask.Response:
    return html_response(render_template("index.html"))


@app.route('/organization', methods=["GET"])
def organization() -> flask.Response:
    return html_response(render_template("organization.html"))


@app.route('/organization/data', methods=["GET", "PUT", "DELETE", "POST"])
def get_organizations() -> flask.Response:
    if request.method == "GET":
        all_organizations = aam.queries.organization.get_all_organizations()
        org_data = [org.to_json() for org in all_organizations]
        return flask.make_response(org_data, 200, {'Content-Type': 'text/json; charset=utf-8'})
    elif request.method == "PUT":
        result = aam.queries.organization.edit_organization(request.json)
        if result.success:
            return flask.make_response("{}", 200, {'Content-Type': 'text/json; charset=utf-8'})
    elif request.method == "POST":
        result = aam.queries.organization.add_new_organization(request.json)
        if result.success:
            return flask.make_response(result.response, 200, {'Content-Type': 'text/json; charset=utf-8'})
    elif request.method == "DELETE":
        result = aam.queries.organization.delete_organization(request.json[0])
        if result.success:
            return flask.make_response("{}", 200, {'Content-Type': 'text/json; charset=utf-8'})
        else:
            return flask.make_response("{}", 500, {'Content-Type': 'text/json; charset=utf-8'})


@app.route('/account', methods=["GET"])
def account() -> flask.Response:
    return html_response(render_template("account.html"))


@app.route('/account/data', methods=["GET"])
def get_accounts() -> flask.Response:
    if request.method == "GET":
        all_accounts = aam.queries.account.get_all_accounts()
        account_data = []
        for acc in all_accounts:
            account_data.append({"account_id": acc.id, "name": acc.name, "organization": acc.organization.name,
                                 "status": acc.status})
        return flask.make_response(all_accounts, 200, {'Content-Type': 'text/json; charset=utf-8'})
    elif request.method == "POST":
        pass