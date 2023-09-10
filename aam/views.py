import flask
from flask import render_template, request

from aam import app
import aam.queries.organization
import aam.queries.account
from aam.utilities import Result


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
    elif request.method == "POST":
        result = aam.queries.organization.add_new_organization(request.json)
        return make_response(result)
    elif request.method == "PUT":
        result = aam.queries.organization.edit_organization(request.json)
        return make_response(result)
    elif request.method == "DELETE":
        result = aam.queries.organization.delete_organization(request.json[0])
        return make_response(result)


@app.route('/account', methods=["GET"])
def account() -> flask.Response:
    return html_response(render_template("account.html"))


@app.route('/account/data', methods=["GET", "POST", "PUT", "DELETE"])
def get_accounts() -> flask.Response:
    if request.method == "GET":
        all_accounts = aam.queries.account.get_all_accounts()
        account_data = [acc.to_json() for acc in all_accounts]
        return flask.make_response(account_data, 200, {'Content-Type': 'text/json; charset=utf-8'})
    elif request.method == "POST":
        result = aam.queries.account.add_new_account(request.json)
        return make_response(result)
    elif request.method == "PUT":
        result = aam.queries.account.edit_account(request.json)
        return make_response(result)
    elif request.method == "DELETE":
        result = aam.queries.account.delete_account(request.json[0])
        return make_response(result)


def make_response(result: Result):
    if result.success:
        return flask.make_response(result.response, 200, {'Content-Type': 'text/json; charset=utf-8'})
    else:
        return flask.make_response(result.response, 500, {'Content-Type': 'text/json; charset=utf-8'})