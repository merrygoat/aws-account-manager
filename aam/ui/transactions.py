import datetime
import decimal
from decimal import Decimal
from typing import TYPE_CHECKING, Iterable, Optional

import nicegui.events
from nicegui import ui

import aam.utilities
from aam import utilities
from aam.models import Account, Person, RechargeRequest, Transaction, MonthlyUsage, TRANSACTION_TYPES

if TYPE_CHECKING:
    from aam.main import UIMainForm


class UITransactions:
    def __init__(self, parent: "UIMainForm"):
        self.parent = parent

        self.new_transaction_dialog = UINewSingleTransactionDialog(self)

        ui.label("Account Transaction Journal").classes("text-4xl")
        self.transaction_grid = ui.aggrid({
            'defaultColDef': {"suppressMovable": True, "sortable": False},
            'columnDefs': [{"headerName": "id", "field": "id", "hide": True},
                           {"headerName": "Date", "field": "date", "editable": True},
                           {"headerName": "Type", "field": "type", "editable": True,
                            "cellEditor": 'agSelectCellEditor',
                            "cellEditorParams": {"values": TRANSACTION_TYPES}},
                           {"headerName": "Currency", "field": "currency", "editable": True},
                           {"headerName": "Net Amount", "field": "amount", "editable": True,
                            "valueFormatter": 'value.toFixed(2)'},
                           {"headerName": "Net Shared Charges ($)", "field": "shared_charge",
                            "valueFormatter": 'value.toFixed(2)'},
                           {"headerName": "Net Support Charge ($)", "field": "support_charge",
                            "valueFormatter": 'value.toFixed(2)'},
                           {"headerName": "Gross Total ($)", "field": "gross_total_dollar",
                            "valueFormatter": 'value.toFixed(2)'},
                           {"headerName": "Gross Total (£)", "field": "gross_total_pound",
                            "valueFormatter": 'value.toFixed(2)'},
                           {"headerName": "Running Total (£)", "field": "running_total",
                            "valueFormatter": 'value.toFixed(2)'},
                           {"headerName": "Reference", "field": "reference", "editable": True},
                           {"headerName": "Project Code", "field": "project_code", "editable": True},
                           {"headerName": "Task Code", "field": "task_code", "editable": True},
                           {"headerName": "Note", "field": "note", "editable": True}],
            'rowData': {},
            'rowSelection': 'multiple',
            'stopEditingWhenCellsLoseFocus': True,
        })

        self.transaction_grid.on("cellValueChanged", self.update_transaction)
        with ui.row():
            ui.button("Add new transaction", on_click=self.add_new_transaction)
            ui.button("Delete selected transaction", on_click=self.delete_selected_transaction)
        ui.separator()

        with ui.row().classes('w-full no-wrap'):
            self.ui_recharge_requests = UIRechargeRequests(self)

    def initialize(self, account: Account | None):
        """This function is run when an account is selected from the dropdown menu."""
        if account is not None:
            self.update_transaction_grid()

    def add_new_transaction(self):
        account_id = self.parent.get_selected_account_id()
        if account_id is None:
            ui.notify("No account selected to add transaction")
            return 0

        self.new_transaction_dialog.open(account_id)

    async def delete_selected_transaction(self, event: nicegui.events.ClickEventArguments):
        selected_rows = await(self.get_selected_rows())
        if selected_rows is None:
            ui.notify("No recharge request selected")

        transaction_types = [row["type"] for row in selected_rows]
        if "Monthly" in transaction_types:
            ui.notify("Monthly type transactions can not be deleted.")
            return 0

        transaction_ids = [row["id"] for row in selected_rows]

        transactions = Transaction.select().where(Transaction.id.in_(transaction_ids))
        for transaction in transactions:
            transaction.delete_instance()
            self.update_transaction_grid()
            selected_request_row = await(self.ui_recharge_requests.request_grid.get_selected_row())
            if selected_request_row:
                self.ui_recharge_requests.update_request_items_grid(selected_request_row["id"])
            ui.notify("Transaction deleted.")

    def update_transaction_grid(self):
        account_id = self.parent.get_selected_account_id()
        if account_id is None:
            row_data = []
        else:
            account = Account.get(Account.id == account_id)
            row_data = account.get_transactions()

        # sort transactions by date and add running total
        row_data = sorted(row_data, key=lambda d: d['date'])
        running_total = 0
        for index, row in enumerate(row_data):
            running_total += row["gross_total_pound"]
            row["running_total"] = running_total

        self.transaction_grid.options["rowData"] = row_data
        self.transaction_grid.update()

    def update_transaction(self, event: nicegui.events.GenericEventArguments):
        """Called when the value of a cell in the transaction grid is changed."""
        if not self._validate_cell_change(event):
            return 0

        transaction_id = event.args["data"]["id"]
        transaction_type = event.args["data"]["type"]
        cell_edited = event.args["colId"]

        if transaction_type == "Monthly":
            transaction: MonthlyUsage = MonthlyUsage.get(id=transaction_id)
        else:
            transaction: Transaction = Transaction.get(id=transaction_id)

        if cell_edited == "date":
            transaction.nominal_date =  event.args["data"]["date"]
        elif cell_edited == "type":
            transaction.type = event.args["data"]["type"]
        elif cell_edited == "amount":
            amount = event.args["data"]["amount"]
            if amount is not None:
                amount = decimal.Decimal(amount)
            transaction.amount = amount
        elif cell_edited == "project_code":
            transaction.project_code = event.args["data"]["project_code"]
        elif cell_edited == "task_code":
            transaction.task_code = event.args["data"]["task_code"]
        elif cell_edited == "reference":
            transaction.reference = event.args["data"]["reference"]
        elif cell_edited == "note":
            transaction.note = event.args["data"]["note"]
        transaction.save()
        self.update_transaction_grid()
        ui.notify(f"Transaction {cell_edited} updated.")

    def _validate_cell_change(self, event: nicegui.events.GenericEventArguments) -> bool:
        """Validate whether a change made to the Transaction gird is valid.

        :param event: The data from the cellValueChanged aggrid event.

        Returns True if change is valid else returns False
        """
        # Only change db as a result of callbacks triggered by user, otherwise we can get stuck in a loop.
        if "source" not in event.args:
            return False

        # Fields that cannot be edited for MonthlyUsage
        invalid_monthly_fields = ["date", "reference", "project_code", "task_code"]
        transaction_type = event.args["data"]["type"]
        cell_edited = event.args["colId"]


        invalid_change = False
        if cell_edited == "type" and event.args["oldValue"] == "Monthly":
            invalid_change = True
        if cell_edited in invalid_monthly_fields and transaction_type == "Monthly":
            invalid_change = True

        if invalid_change:
            ui.notify(f'Can not change field "{cell_edited}" for "Monthly" type transactions.')
            self.transaction_grid.run_row_method(event.args['rowId'], 'setDataValue', cell_edited, event.args["oldValue"])
            return False

        if cell_edited == "amount" and event.args["newValue"] is not None:
            try:
                decimal.Decimal(event.args["newValue"])
            except decimal.InvalidOperation:
                ui.notify("Invalid amount for transaction - must be a number")
                self.transaction_grid.run_row_method(event.args['rowId'], 'setDataValue', 'amount', event.args["oldValue"])
                return False
        return True

    async def get_selected_rows(self) -> list[dict]:
        return await(self.transaction_grid.get_selected_rows())


class UIRechargeRequests:
    def __init__(self, parent: UITransactions):
        self.parent = parent

        self.new_request_dialog = UINewRechargeDialog(self)

        with ui.column().classes("w-1/4"):
            ui.label("Recharge Requests").classes("text-4xl")
            self.request_grid = ui.aggrid({
                'columnDefs': [{"headerName": "request_id", "field": "id", "hide": True},
                               {"headerName": "Date", "field": "date", "sort": "asc", "sortIndex": 0},
                               {"headerName": "Reference", "field": "reference", "editable": True},
                               {"headerName": "Status", "field": "status", 'editable': True,
                                'cellEditor': 'agSelectCellEditor',
                                'cellEditorParams': {'values': ['Draft', 'Submitted', 'Completed']}}],
                'rowData': {},
                'rowSelection': 'single',
                'stopEditingWhenCellsLoseFocus': True,
            })
            with ui.row():
                self.add_request_button = ui.button("Add new request", on_click=self.new_request_dialog.open)
                self.delete_selected_request_button = ui.button("Delete selected request", on_click=self.delete_selected_request)

        with ui.column().classes("w-1/2"):
            ui.label("Request items").classes("text-4xl")
            self.request_items_grid = ui.aggrid({
                'columnDefs': [{"headerName": "transaction_id", "field": "transaction_id", "hide": True},
                               {"headerName": "Account", "field": "account_name", "sort": "asc", "sortIndex": 0},
                               {"headerName": "Account ID", "field": "account_id"},
                               {"headerName": "Date", "field": "date", "sort": "asc", "sortIndex": 1},
                               {"headerName": "Type", "field": "type"},
                               {"headerName": "Amount (£)", "field": "recharge_amount",
                                "valueFormatter": "value.toFixed(2)"}],
                'rowData': {},
                'rowSelection': 'multiple',
                'stopEditingWhenCellsLoseFocus': True,
            })
            with ui.row():
                self.add_to_recharge_request_button = ui.button("Add selected transactions to request", on_click=self.add_transaction_to_request)
                self.remove_recharge_button = ui.button("Remove selected transactions from request", on_click=self.remove_transaction_from_request)

        with ui.column().classes("w-1/4"):
            ui.label("Request summary").classes("text-4xl")
            self.request_summary_grid = ui.aggrid({
                'columnDefs': [{"headerName": "Account ID", "field": "account_id", "hide": True},
                               {"headerName": "Account", "field": "account_name", "sort": "asc", "sortIndex": 0},
                               {"headerName": "Amount (£)", "field": "recharge_amount", "valueFormatter": "value.toFixed(2)"}],
                'rowData': {}
            })

        self.request_grid.on('rowSelected', self.request_row_selected)
        self.request_grid.on('cellValueChanged', self.request_edited)
        self.populate_request_grid()
        self.request_items_grid.on("cellDoubleClicked", self.cell_clicked)
        self.request_summary_grid.on("cellDoubleClicked", self.cell_clicked)

    async def get_selected_recharge_id(self) -> Optional[str]:
        selected_row = await(self.request_grid.get_selected_row())
        if selected_row is None:
            return None
        return selected_row["id"]

    def request_row_selected(self, event: nicegui.events.GenericEventArguments):
        if event.args["selected"] is True:
            self.update_request_items_grid(event.args["data"]["id"])

    @staticmethod
    def request_edited(event: nicegui.events.GenericEventArguments):
        request_id = event.args["data"]["id"]
        request = RechargeRequest.get(id=request_id)
        request.status = event.args["data"]["status"]
        request.reference = event.args["data"]["reference"]
        request.save()

    def populate_request_grid(self):
        requests: Iterable[RechargeRequest] = RechargeRequest.select()
        request_details = [request.to_json() for request in requests]
        self.request_grid.options["rowData"] = request_details
        self.request_grid.update()

    async def delete_selected_request(self, event: nicegui.events.ClickEventArguments):
        selected_row = await(self.request_grid.get_selected_row())
        if selected_row is None:
            ui.notify("No recharge request selected to delete.")
            return 0
        request: RechargeRequest = RechargeRequest.get(selected_row["id"])
        if request.transactions or request.monthly_usage:
            ui.notify("Recharge request has recharges. These must be removed before deleting the request.")
            return 0
        else:
            ui.notify(f"Request {request.reference} deleted.")
            request.delete_instance()
            self.populate_request_grid()

    async def export_recharge_request(self):
        selected_row = await(self.request_grid.get_selected_row())
        if selected_row is None:
            ui.notify("No recharge request selected to export.")
            return 0

        request_id = selected_row["id"]
        transactions = (Transaction.select(Transaction, Account, Person)
                        .join(Account)
                        .join(Person)
                        .where(Transaction.recharge_request == request_id))
        usage = (MonthlyUsage.select(MonthlyUsage, Account, Person)
                 .join(Account)
                 .join(Person)
                 .where(MonthlyUsage.recharge_request == request_id))

        transactions = list(transactions)
        transactions.extend(list(usage))

        if not transactions:
            ui.notify("Cannot export recharge request as it has no recharges.")
            return 0

        # Group transactions by account
        transaction_dict = {}
        for transaction in transactions:
            transaction_dict.setdefault(transaction.account.id, []).append(transaction)

        export_string = "Account Number, Account Name, Budget Holder Name, Budget Holder Email, CC email, Finance Code, Task Code, Total\n"
        for account_number, transactions in transaction_dict.items():
            total = Decimal(0)
            for transaction in transactions:
                total += transaction.gross_total_pound
            total = round(total, 2)
            account = transactions[0].account
            export_string += f"{account_number}, {account.name}, {account.budget_holder.first_name}, {account.budget_holder.email}, , {account.finance_code}, {account.task_code}, {total}\n"

        recharge_request = RechargeRequest.get(id=request_id)
        ui.download(bytes(export_string, 'utf-8'), f"{recharge_request.reference} export.txt")

    def cell_clicked(self, event: nicegui.events.GenericEventArguments):
        account: Account = Account.get(Account.id == event.args["data"]["account_id"])
        self.parent.parent.change_selected_organization(account.organization_id)
        self.parent.parent.change_selected_account(account.id)

    def update_request_items_grid(self, request_id: int | None):
        if request_id is None:
            return 0

        transactions: Iterable[Transaction] = (Transaction.select(Transaction, Account)
                                               .join(Account)
                                               .where(Transaction.recharge_request == request_id))
        monthly_usage: Iterable[MonthlyUsage] = (MonthlyUsage.select(MonthlyUsage, Account)
                                         .join(Account)
                                         .where(MonthlyUsage.recharge_request == request_id))

        # For the properties exposed in the grid we can treat Transactions and MonthlyUsage as the same type of object.
        items = list(transactions)
        items.extend(list(monthly_usage))

        recharges_list = []
        account_totals = {}

        for item in items:
            recharges_list.append({"transaction_id": item.id, "account_name": item.account.name,
                                   "account_id": item.account.id, "date": item.date, "type": item.type,
                                   "recharge_amount": item.gross_total_pound})
            if item.account.id not in account_totals:
                account_totals[item.account.id] = {"account_name": item.account.name, "account_id": item.account.id,
                                                   "recharge_amount": 0}
            account_totals[item.account.id]["recharge_amount"] += item.gross_total_pound

        self.request_items_grid.options["rowData"] = recharges_list
        self.request_items_grid.update()
        self.request_summary_grid.options["rowData"] = list(account_totals.values())
        self.request_summary_grid.update()

    async def add_transaction_to_request(self, event: nicegui.events.ClickEventArguments):
        """Get selected Transactions and MonthlyUsage and add them to the recharge request."""
        selected_request_row = await(self.parent.ui_recharge_requests.request_grid.get_selected_row())
        if not selected_request_row:
            ui.notify("No recharge request selected")
            return 0
        selected_recharge_id = selected_request_row["id"]

        selected_transaction_rows = await(self.parent.parent.transactions.get_selected_rows())
        if not selected_transaction_rows:
            ui.notify("No transactions selected")
            return 0

        monthly_ids = []
        transaction_ids = []
        for row in selected_transaction_rows:
            if row["type"] == "Monthly":
                monthly_ids.append(row["id"])
            else:
                transaction_ids.append(row["id"])

        # Can combine MonthlyUsage and Transactions as they both have the required properties.
        usage = list(MonthlyUsage.select().where(MonthlyUsage.id.in_(monthly_ids)))
        transactions = list(Transaction.select().where(Transaction.id.in_(transaction_ids)))
        transactions.extend(usage)

        for transaction in transactions:
            if transaction.amount is None:
                ui.notify(f"Cannot add transaction for date {str(transaction.date)} as it has no recorded usage.")
            else:
                transaction.recharge_request = selected_recharge_id
                transaction.save()

        self.parent.update_transaction_grid()
        self.update_request_items_grid(selected_recharge_id)

    async def remove_transaction_from_request(self):
        selected_rows = await(self.request_items_grid.get_selected_rows())

        if selected_rows is None:
            ui.notify("No transactions selected to remove.")
            return 0

        selected_usage = []
        selected_transactions = []
        for row in selected_rows:
            if row["type"] == "Monthly":
                selected_usage.append(row["transaction_id"])
            else:
                selected_transactions.append(row["transaction_id"])

        if selected_usage:
            usage = MonthlyUsage.select().where(MonthlyUsage.id.in_(selected_usage))
            for month in usage:
                month.recharge_request = None
                month.save()

        if selected_transactions:
            transactions = Transaction.select().where(Transaction.id.in_(selected_transactions))
            for transaction in transactions:
                transaction.recharge_request = None
                transaction.save()

        selected_request_row = await(self.parent.ui_recharge_requests.request_grid.get_selected_row())
        selected_request_id = selected_request_row["id"]

        self.update_request_items_grid(selected_request_id)
        self.parent.update_transaction_grid()


class UINewSingleTransactionDialog:
    def __init__(self, parent: UITransactions):
        self.parent = parent
        self.selected_account_id: int | None = None

        with ui.dialog() as self.dialog:
            with ui.card():
                ui.label("New transaction").classes("text-2xl")
                with ui.grid(columns="auto auto"):
                    ui.label("Date")
                    self.date_input = utilities.date_picker()
                    ui.label("Type")
                    self.type = ui.select(options=TRANSACTION_TYPES).classes("q-field--dense")
                    ui.label("Currency")
                    self.currency_toggle = ui.radio(["Pound", "Dollar"], value="Pound", on_change=self.change_currency).props('inline')
                    ui.label("Amount")
                    self.amount = ui.input()
                    self.exchange_rate_label = ui.label("Exchange rate (USD/GBP)")
                    self.exchange_rate = ui.input("Exchange rate")
                    ui.button("Add", on_click=self.new_transaction)
                    ui.button("Cancel", on_click=self.dialog.close)
        self.set_currency(True)

    def open(self, account_id: str | int):
        self.selected_account_id = account_id
        self.dialog.open()

    def new_transaction(self):
        if not self.date_input.value:
            ui.notify("Must specify transaction date.")
            return 0

        if not self.type.value:
            ui.notify("Must specify transaction type.")
            return 0

        amount = self.amount.value

        try:
            amount = decimal.Decimal(amount)
        except decimal.InvalidOperation:
            ui.notify("Invalid value for amount. Must be a number.")
            return 0

        if self.currency_toggle.value == "Dollar":
            exchange_rate = Decimal(self.exchange_rate.value)
            is_pound = False
        else:
            exchange_rate = None
            is_pound = True

        Transaction.create(account=self.selected_account_id, date=self.date_input.value,
                           _type=TRANSACTION_TYPES.index(self.type.value), amount=amount, is_pound=is_pound,
                           exchange_rate=exchange_rate)
        self.parent.update_transaction_grid()
        ui.notify("New transaction added.")
        self.dialog.close()

    def change_currency(self, event: nicegui.events.ValueChangeEventArguments):
        self.set_currency(bool(event.value == "Pound"))

    def set_currency(self, pound: bool):
        self.exchange_rate_label.set_visibility(not pound)
        self.exchange_rate.set_visibility(not pound)


class UINewRechargeDialog:
    def __init__(self, parent: UIRechargeRequests):
        self.parent = parent
        with ui.dialog() as self.dialog:
            with ui.card():
                ui.label("New recharge request").classes("text-2xl")
                with ui.grid(columns="auto auto"):
                    ui.label("Date")
                    self.date_input = utilities.date_picker(datetime.date.today())
                    ui.label("Reference")
                    self.reference_input = ui.input(validation={"Must provide reference": lambda value: len(value) > 1})
                    ui.label("Auto populate recharges")
                    self.auto_populate = ui.switch(value=False)
                    with ui.row():
                        ui.label("Start month")
                        self.start_month = utilities.month_select()
                    with ui.row():
                        ui.label("Start year")
                        self.start_year = utilities.year_select()
                    with ui.row():
                        ui.label("End month")
                        self.end_month = utilities.month_select()
                    with ui.row():
                        ui.label("End year")
                        self.end_year = utilities.year_select()
                    ui.button("Add", on_click=self.new_recharge_request)
                    ui.button("Cancel", on_click=self.dialog.close)

        self.start_month.bind_enabled_from(self.auto_populate, "value")
        self.start_year.bind_enabled_from(self.auto_populate, "value")
        self.end_month.bind_enabled_from(self.auto_populate, "value")
        self.end_year.bind_enabled_from(self.auto_populate, "value")

    def open(self):
        self.dialog.open()

    def close(self):
        self.dialog.close()

    def new_recharge_request(self, event: nicegui.events.ClickEventArguments):
        start_month_code = None
        end_month_code = None
        if self.auto_populate.value is True:
            start_month_code = aam.utilities.month_code(self.start_year.value, self.start_month.value)
            end_month_code = aam.utilities.month_code(self.end_year.value, self.end_month.value)
            if end_month_code < start_month_code:
                ui.notify("End month must be after start month.")
                return 0

        if self.reference_input.value != "":
            recharge_request = RechargeRequest.create(date=datetime.date.fromisoformat(self.date_input.value),
                                                      reference=self.reference_input.value, status="Draft")
        else:
            ui.notify("Must provide a reference")
            return 0

        if self.auto_populate.value is True:
            self.add_transactions_to_request(start_month_code, end_month_code, recharge_request)

        ui.notify("New recharge request added")
        self.parent.parent.ui_recharge_requests.populate_request_grid()
        self.close()

    @staticmethod
    def add_transactions_to_request(start_month_code: int, end_month_code: int, recharge_request: RechargeRequest):
        """Find any Transaction or MonthlyUsage between the start of `start_month` and the end of `end_month` and
        add them to the recharge request."""
        start_date = aam.utilities.date_from_month_code(start_month_code)
        end_date = aam.utilities.date_from_month_code(end_month_code + 1)
        transactions: Iterable[Transaction] = (Transaction.select(Transaction, Account)
                                               .join(Account)
                                               .where((Account.is_recharged == True) & (Transaction.date > start_date) & (Transaction.date < end_date)))
        for transaction in transactions:
            if not transaction.recharge_request:
                transaction.recharge_request = recharge_request.id
                transaction.save()
            else:
                ui.notify(
                    f"Transaction for account: {transaction.account.name}, date: {transaction.date} is already assigned to another recharge.")

        usage = (MonthlyUsage.select(MonthlyUsage, Account)
                 .join(Account)
                 .where(
            (Account.is_recharged == True) & (MonthlyUsage.month_id >= start_month_code) & (MonthlyUsage.month_id <= end_month_code)))
        for month_usage in usage:
            if not month_usage.recharge_request:
                month_usage.recharge_request = recharge_request.id
                month_usage.save()
            else:
                ui.notify(
                    f"MonthlyUsage for account: {month_usage.account.name}, date: {month_usage.date} is already assigned to another recharge.")
