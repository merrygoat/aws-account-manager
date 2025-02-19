from typing import TYPE_CHECKING

from nicegui import ui

from aam.models import Account, Organization

if TYPE_CHECKING:
    from aam.main import UIMainForm


class UIDataQuality:
    def __init__(self, parent: "UIMainForm"):
        self.parent = parent

        with ui.tabs().props("align left").classes('w-full') as tabs:
            tab_one = ui.tab("Account Dates")
            tab_two = ui.tab("Monthly Usage")

        with ui.tab_panels(tabs, value=tab_one).classes('w-full'):
            with ui.tab_panel(tab_one):
                with ui.column().classes('w-full no-wrap'):
                    ui.label("Account Open/Close dates").classes("text-2xl")
                    ui.label("Accounts with no open date")
                    self.no_open_grid = ui.aggrid({
                        'defaultColDef': {"suppressMovable": True},
                        'columnDefs': [{"headerName": "Account", "field": "account_name", "sort": "desc"},
                                       {"headerName": "Organization", "field": "organization_name"}
                                       ],
                        'rowData': {}})
                    ui.button("Refresh list", on_click=self.populate_no_open_grid())
                    ui.label("Closed/Suspended accounts with no close date")
                    self.no_close_grid = ui.aggrid({
                        'defaultColDef': {"suppressMovable": True},
                        'columnDefs': [{"headerName": "Account", "field": "account_name", "sort": "desc"},
                                       {"headerName": "Organization", "field": "organization_name"},
                                       {"headerName": "Account Status", "field": "account_status"}
                                       ],
                        'rowData': {}})
                    ui.button("Refresh list", on_click=self.populate_no_close_grid())

            with ui.tab_panel(tab_two):
                with ui.column().classes('w-full no-wrap'):
                    ui.html("Accounts Missing Monthly Usage").classes("text-2xl")
                    self.missing_usage = ui.aggrid({
                        'defaultColDef': {"suppressMovable": True},
                        'columnDefs': [{"headerName": "Account", "field": "account_name", "sort": "desc"},
                                       {"headerName": "Organization", "field": "organization_name"},
                                       {"headerName": "Number of Months Missing", "field": "num_months"}
                                       ],
                        'rowData': {}})
                    ui.button("Refresh list", on_click=self.populate_no_close_grid())

            self.populate_no_open_grid()
            self.populate_no_close_grid()
            self.populate_missing_usage_grid()


    def populate_no_open_grid(self):
        accounts = Account.select().join(Organization).where(Account.creation_date.is_null(True))
        account_details = [{"account_name": account.name, "organization_name": account.organization.name}
                           for account in accounts]
        self.no_open_grid.options["rowData"] = account_details
        self.no_open_grid.update()

    def populate_no_close_grid(self):
        account_status = ["Closed", "SUSPENDED"]
        accounts = Account.select().join(Organization).where((Account.status.in_(account_status) & Account.closure_date.is_null(True)))
        account_details = [{"account_name": account.name, "organization_name": account.organization.name,
                            "account_status": account.status} for account in accounts]
        self.no_close_grid.options["rowData"] = account_details
        self.no_close_grid.update()

    def populate_missing_usage_grid(self):
        pass