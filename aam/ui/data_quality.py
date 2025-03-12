import datetime
from typing import TYPE_CHECKING, Iterable

import nicegui.events
from nicegui import ui

from aam.models import Account, Organization, MonthlyUsage, Transaction
import aam.utilities

if TYPE_CHECKING:
    from aam.main import UIMainForm


class UIDataQuality:
    def __init__(self, parent: "UIMainForm"):
        self.parent = parent

        with ui.tabs().props("align left").classes('w-full') as tabs:
            tab_one = ui.tab("Account Dates")
            tab_two = ui.tab("Monthly Usage")
            tab_three = ui.tab("Other Transactions")

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
                    ui.label("Accounts Missing Monthly Usage").classes("text-2xl")
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

                    ui.label("Accounts with Monthly Usage outside of open/close dates").classes("text-2xl")
                    self.wrong_monthly_usage = ui.aggrid({
                        'defaultColDef': {"suppressMovable": True},
                        'columnDefs': [{"headerName": "MonthlyUsageID", "field": "id"},
                                       {"headerName": "Account", "field": "account_name"},
                                       {"headerName": "Account ID", "field": "account_id", "sort": "asc"},
                                       {"headerName": "Date", "field": "date"},
                                       {"headerName": "Usage", "field": "usage"}
                                       ],
                        'rowSelection': 'multiple',
                        'rowData': {}})
                    with ui.row():
                        ui.button("Refresh list", on_click=self.populate_wrong_monthly_usage)
                        ui.button("Delete selected months", on_click=self.delete_selected_monthly_usage)

            with ui.tab_panel(tab_three):
                with ui.column().classes('w-full no-wrap'):
                    ui.label("Recharge Transactions without project code").classes("text-2xl")
                    self.recharges_missing_code_grid = ui.aggrid({
                        'defaultColDef': {"suppressMovable": True},
                        'columnDefs': [{"headerName": "Account", "field": "account_name"},
                                       {"headerName": "Account ID", "field": "account_id", "sort": "asc"},
                                       {"headerName": "Date", "field": "transaction_date"}
                                       ],
                        'rowSelection': 'multiple',
                        'rowData': {}})
                    ui.button("Refresh list", on_click=self.populate_recharges_missing_code_grid)

            self.populate_no_open_grid()
            self.populate_no_close_grid()
            self.populate_recharges_missing_code_grid()

    def populate_no_open_grid(self):
        accounts = (Account.select()
                    .join(Organization)
                    .where(Account.creation_date.is_null(True)))
        account_details = [{"account_name": account.name, "organization_name": account.organization.name}
                           for account in accounts]
        self.no_open_grid.options["rowData"] = account_details
        self.no_open_grid.update()

    def populate_no_close_grid(self):
        account_status = ["Closed", "SUSPENDED"]
        accounts = (Account.select()
                    .join(Organization)
                    .where((Account.status.in_(account_status) & Account.closure_date.is_null(True))))
        account_details = [{"account_name": account.name, "organization_name": account.organization.name,
                            "account_status": account.status} for account in accounts]
        self.no_close_grid.options["rowData"] = account_details
        self.no_close_grid.update()

    def populate_recharges_missing_code_grid(self):
        transactions: Iterable[Transaction] = (Transaction.select(Transaction, Account.name, Account.id)
                                               .join(Account)
                                               .where((Transaction._type == 3) & (Transaction.project_code.is_null())))
        transaction_details = [{"account_name": transaction.account.name, "account_id": transaction.account_id,
                                "transaction_date": transaction.date} for transaction in transactions]
        self.recharges_missing_code_grid.options["rowData"] = transaction_details
        self.recharges_missing_code_grid.update()

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

    def populate_wrong_monthly_usage(self):
        """Remove any MonthlyUsage transactions which fall before the opening date or after the closing date of an
        account."""
        all_usage: Iterable[MonthlyUsage] = MonthlyUsage.select(MonthlyUsage, Account).join(Account)
        usage_details = []
        for usage in all_usage:
            account: Account = usage.account
            if not account.creation_date:
                pass
            start_month = aam.utilities.month_code(account.creation_date.year, account.creation_date.month)
            if account.closure_date:
                end_month = aam.utilities.month_code(account.closure_date.year, account.closure_date.month)
            else:
                end_month = aam.utilities.month_code(datetime.date.today().year, datetime.date.today().month)
            if usage.month_id < start_month or usage.month_id > end_month:
                usage_details.append({"id": usage.id, "account_name": usage.account.name,
                                      "account_id": usage.account.id, "date": usage.date, "usage": usage.amount})
        self.wrong_monthly_usage.options["rowData"] = usage_details
        self.wrong_monthly_usage.update()

    async def delete_selected_monthly_usage(self, event: nicegui.events.ClickEventArguments):
        selected_rows = await(self.wrong_monthly_usage.get_selected_rows())
        if not selected_rows:
            ui.notify("No rows selected to delete.")
            return 0
        monthly_usage_ids = [row["id"] for row in selected_rows]
        query = MonthlyUsage.delete().where(MonthlyUsage.id.in_(monthly_usage_ids))
        rows_deleted = query.execute()
        self.populate_wrong_monthly_usage()
        ui.notify(f"{rows_deleted} rows deleted")
