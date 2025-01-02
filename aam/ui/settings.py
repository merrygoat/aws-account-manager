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
        self.new_org_dialog = UINewOrganizationDialog(self)

        self.organization_grid = ui.aggrid({
            "defaultColDef": {"sortable": False},
            'columnDefs': [{"headerName": "id", "field": "id"},
                           {"headerName": "Name", "field": "name", "editable": True}],
            'rowData': {},
            'rowSelection': 'single',
            'stopEditingWhenCellsLoseFocus': True,
        })
        self.add_new_org = ui.button("Add new organization", on_click=self.new_org_dialog.open)
        self.delete_organization = ui.button("Delete selected organization", on_click=self.delete_organization)
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

    async def delete_organization(self, event: nicegui.events.ClickEventArguments):
        selected_org = await(self.organization_grid.get_selected_row())
        if selected_org:
            organization = Organization.get(Organization.id == selected_org["id"])
            if list(organization.accounts):
                ui.notify("Cannot delete Organization as it has accounts associated with it.")
            else:
                organization.delete_instance()
                ui.notify("Organization successfully deleted")
                self.populate_org_grid()
        else:
            ui.notify("No organization selected to delete.")

class UINewOrganizationDialog:
    def __init__(self, parent: UIOrganizations):
        self.parent = parent
        with ui.dialog() as self.dialog:
            with ui.card():
                ui.label("New Organization").classes("text-2xl")
                with ui.grid(columns="auto auto"):
                    ui.label("Organization ID")
                    self.name = ui.input(validation={"Must provide organization ID": lambda value: len(value) > 1})
                    ui.button("Add", on_click=self.new_organization)
                    ui.button("Cancel", on_click=self.dialog.close)

    def open(self):
        self.dialog.open()

    def close(self):
        self.dialog.close()

    def new_organization(self, event: nicegui.events.ClickEventArguments):
        if self.name.value != "":
            Organization.create(id=self.name.value)
            ui.notify("New organization added")
            self.parent.populate_org_grid()
            self.close()
        else:
            ui.notify("Must provide an organization name")
