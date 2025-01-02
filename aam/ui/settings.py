from typing import TYPE_CHECKING

from nicegui import ui
import nicegui.events

from aam.models import Month, Organization

if TYPE_CHECKING:
    from aam.main import UIMainForm


class UISettings:
    def __init__(self, parent: "UIMainForm"):
        self.parent = parent

        ui.label("Settings").classes("text-4xl")
        with ui.column().classes("w-full"):
            ui.label("Exchange Rate").classes("text-xl")
            self.ui_exchange_rate = UIExchangeRate(self)
            ui.label("Organizations").classes("text-xl")
            self.ui_organizations = UIOrganizations(self)


class UIExchangeRate:
    def __init__(self, parent: UISettings):
        self.parent = parent

        self.month_grid = ui.aggrid({
            "defaultColDef": {"sortable": False},
            'columnDefs': [{"headerName": "id", "field": "id", "hide": True},
                           {"headerName": "Month", "field": "month", "cellDataType": "string"},
                           {"headerName": "Exchange rate £/$", "field": "exchange_rate", "editable": True}],
            'rowData': {},
            'stopEditingWhenCellsLoseFocus': True,
        })
        self.month_grid.on("cellValueChanged", self.update_exchange_rate)
        self.populate_exchange_rate_grid()

    def populate_exchange_rate_grid(self):
        months = [{"id": month.id, "month": str(month), "exchange_rate": month.exchange_rate} for month in Month.select()]
        self.month_grid.options["rowData"] = months
        self.month_grid.update()

    @staticmethod
    def update_exchange_rate(event: nicegui.events.GenericEventArguments):
        month_id = event.args["data"]["id"]
        month = Month.get(id=month_id)
        month.exchange_rate = event.args["data"]["exchange_rate"]
        month.save()


class UIOrganizations:
    def __init__(self, parent: UISettings):
        self.parent = parent

        self.organization_grid = ui.aggrid({
            "defaultColDef": {"sortable": False},
            'columnDefs': [{"headerName": "id", "field": "id"},
                           {"headerName": "Name", "field": "name", "editable": True}],
            'rowData': {},
            'stopEditingWhenCellsLoseFocus': True,
        })
        self.organization_grid.on("cellValueChanged", self.update_org_name)
        self.populate_org_grid()

    def populate_org_grid(self):
        orgs = [{"id": org.id, "name": org.name} for org in Organization.select()]
        self.organization_grid.options["rowData"] = orgs
        self.organization_grid.update()

    @staticmethod
    def update_org_name(event: nicegui.events.GenericEventArguments):
        org_id = event.args["data"]["id"]
        org = Organization.get(id=org_id)
        org.name = event.args["data"]["name"]
        org.save()
