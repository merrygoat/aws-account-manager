import datetime
from typing import TYPE_CHECKING, Iterable

from nicegui import ui

from aam.models import Account, Organization, MonthlyUsage
import aam.utilities

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
                    ui.button("Refresh list", on_click=self.populate_no_open_grid)

                    ui.label("Closed/Suspended accounts with no close date")
                    self.no_close_grid = ui.aggrid({
                        'defaultColDef': {"suppressMovable": True},
                        'columnDefs': [{"headerName": "Account", "field": "account_name", "sort": "desc"},
                                       {"headerName": "Organization", "field": "organization_name"},
                                       {"headerName": "Account Status", "field": "account_status"}
                                       ],
                        'rowData': {}})
                    ui.button("Refresh list", on_click=self.populate_no_close_grid)

            with ui.tab_panel(tab_two):
                with ui.column().classes('w-full no-wrap'):
                    ui.html("Accounts Missing Monthly Usage").classes("text-2xl")
                    self.missing_usage = ui.aggrid({
                        'defaultColDef': {"suppressMovable": True},
                        'columnDefs': [{"headerName": "Account", "field": "account_name"},
                                       {"headerName": "Account ID", "field": "account_id", "sort": "asc"},
                                       {"headerName": "Organization", "field": "organization_name"},
                                       {"headerName": "Number of Months Missing", "field": "num_months"},
                                       {"headerName": "Missing Months", "field": "missing_months"}
                                       ],
                        'rowSelection': 'multiple',
                        'rowData': {}})
                    ui.button("Refresh list", on_click=self.populate_missing_usage_grid)

            self.populate_no_open_grid()
            self.populate_no_close_grid()


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
        accounts: Iterable[Account] = (Account.select(Account, Organization.name).join(Organization))
        account_summaries = []
        for account in accounts:
            if account.creation_date:
                required_months = aam.utilities.get_months_between(account.creation_date, account.final_date)
                # Check that all empty months have been generated for the account
                account.check_missing_monthly_transactions(required_months)
                # Remove current month as we don't care that current month is not populated
                current_month = [aam.utilities.month_code(datetime.date.today().year, datetime.date.today().month)]
                required_months = set(required_months) - set(current_month)
                missing_usage_months: Iterable[MonthlyUsage] = (MonthlyUsage.select()
                                                                .where((MonthlyUsage.account_id == account.id)
                                                                       & (MonthlyUsage.month_id.in_(required_months))
                                                                       & (MonthlyUsage.amount.is_null(True)))
                                        )
                num_months = len(list(missing_usage_months))
                if num_months > 0:
                    missing_months = ", ".join([month.date.strftime("%b-%Y") for month in missing_usage_months])
                    account_summaries.append({"account_name": account.name, "account_id": account.id,
                                              "organization_name": account.organization.name,
                                              "num_months": num_months, "missing_months": missing_months})

        self.missing_usage.options["rowData"] = account_summaries
        self.missing_usage.update()