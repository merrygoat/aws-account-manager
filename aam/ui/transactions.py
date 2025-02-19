import datetime
import decimal
from decimal import Decimal
from typing import TYPE_CHECKING, Iterable

import nicegui.events
from nicegui import ui

from aam import utilities
from aam.models import Account, Person, RechargeRequest, Transaction, MonthlyUsage

if TYPE_CHECKING:
    from aam.main import UIMainForm


class UITransactions:
    def __init__(self, parent: "UIMainForm"):
        self.parent = parent

        self.new_request_dialog = UINewRechargeDialog(self)
        self.new_transaction_dialog = UINewSingleTransactionDialog(self)

        ui.label("Account transactions").classes("text-4xl")
        self.transaction_grid = ui.aggrid({
            'defaultColDef': {"suppressMovable": True},
            'columnDefs': [{"headerName": "id", "field": "id", "hide": True},
                           {"headerName": "Date", "field": "date", "sort": "asc"},
                           {"headerName": "Type", "field": "type"},
                           {"headerName": "Currency", "field": "currency", "editable": True,
                            "valueFormatter": "value.toFixed(2)"},
                           {"headerName": "Net Amount", "field": "amount", "editable": True,
                            "valueFormatter": "value.toFixed(2)"},
                           {"headerName": "Net Shared Charges ($)", "field": "shared_charge",
                            "valueFormatter": "value.toFixed(2)"},
                           {"headerName": "Net Support Charge ($)", "field": "support_charge",
                            "valueFormatter": "value.toFixed(2)"},
                           {"headerName": "Gross Total ($)", "field": "gross_total_dollar",
                            "valueFormatter": "value.toFixed(2)"},
                           {"headerName": "Gross Total (£)", "field": "gross_total_pound",
                            "valueFormatter": "value.toFixed(2)"},
                           {"headerName": "Recharge Reference", "field": "recharge_reference"}],
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
            with ui.column().classes("w-1/3"):
                self.ui_recharge_requests = UIRechargeRequests(self)

            with ui.column().classes("w-2/3"):
                self.ui_request_items = UIRequestItems(self)

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
            selected_request_row = await(self.ui_recharge_requests.recharge_request_grid.get_selected_row())
            if selected_request_row:
                self.ui_request_items.update_request_items_grid(selected_request_row["id"])
            ui.notify("Transaction deleted.")

    def update_transaction_grid(self):
        account_id = self.parent.get_selected_account_id()
        if account_id is None:
            row_data = []
        else:
            account = Account.get(Account.id == account_id)
            row_data = account.get_transactions()
        self.transaction_grid.options["rowData"] = row_data
        self.transaction_grid.update()

    def update_transaction(self, event: nicegui.events.GenericEventArguments):
        transaction_id = event.args["data"]["id"]
        transaction_type = event.args["data"]["type"]
        if transaction_type == "Monthly":
            transaction: MonthlyUsage = MonthlyUsage.get(id=transaction_id)
        else:
            transaction: Transaction = Transaction.get(id=transaction_id)
        try:
            amount = decimal.Decimal(event.args["data"]["amount"])
        except decimal.InvalidOperation:
            ui.notify("Invalid amount for transaction - must be a number")
            return 0
        transaction.amount = amount
        transaction.save()
        self.update_transaction_grid()

    async def get_selected_rows(self) -> list[dict]:
        return await(self.transaction_grid.get_selected_rows())


class UIRechargeRequests:
    def __init__(self, parent: UITransactions):
        self.parent = parent

        ui.label("Recharge Requests").classes("text-4xl")
        self.recharge_request_grid = ui.aggrid({
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
            self.add_request_button = ui.button("Add new request", on_click=self.parent.new_request_dialog.open)
            self.delete_selected_request_button = ui.button("Delete selected request", on_click=self.delete_selected_request)
            self.export_recharge_button = ui.button("Export selected request", on_click=self.export_recharge_request)

        self.recharge_request_grid.on('rowSelected', self.row_selected)
        self.recharge_request_grid.on('cellValueChanged', self.recharge_request_edited)
        self.populate_request_grid()

    def row_selected(self, event: nicegui.events.GenericEventArguments):
        if event.args["selected"] is True:
            self.parent.ui_request_items.update_request_items_grid(event.args["data"]["id"])

    @staticmethod
    def recharge_request_edited(event: nicegui.events.GenericEventArguments):
        request_id = event.args["data"]["id"]
        request = RechargeRequest.get(id=request_id)
        request.status = event.args["data"]["status"]
        request.reference = event.args["data"]["reference"]
        request.save()

    def populate_request_grid(self):
        requests: Iterable[RechargeRequest] = RechargeRequest.select()
        request_details = [request.to_json() for request in requests]
        self.recharge_request_grid.options["rowData"] = request_details
        self.recharge_request_grid.update()

    async def delete_selected_request(self, event: nicegui.events.ClickEventArguments):
        selected_row = await(self.recharge_request_grid.get_selected_row())
        if selected_row is None:
            ui.notify("No recharge request selected to delete.")
            return 0
        request = RechargeRequest.get(selected_row["id"])
        if request.transaction:
            ui.notify("Recharge request has recharges. These must be removed before deleting the request.")
            return 0
        else:
            ui.notify(f"Request {request.reference} deleted.")
            request.delete_instance()
            self.populate_request_grid()

    async def export_recharge_request(self):
        selected_row = await(self.recharge_request_grid.get_selected_row())
        if selected_row is None:
            ui.notify("No recharge request selected to export.")
            return 0

        request_id = selected_row["id"]
        transactions = (Transaction.select(Transaction, Account, Person)
                        .join(Account)
                        .join(Person)
                        .where(Transaction.recharge_request == request_id))
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


class UIRequestItems:
    def __init__(self, parent: UITransactions):
        self.parent = parent

        ui.label("Request items").classes("text-4xl")
        self.request_items_grid = ui.aggrid({
            'columnDefs': [{"headerName": "transaction_id", "field": "transaction_id", "hide": True},
                           {"headerName": "Account", "field": "account_name", "sort": "asc", "sortIndex": 0},
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

    def update_request_items_grid(self, request_id: int | None):
        if request_id is None:
            return 0

        transactions = (Transaction.select(Transaction, Account)
                        .join(Account)
                        .where(Transaction.recharge_request == request_id))
        recharges_list = []
        for transaction in transactions:
            recharges_list.append({"transaction_id": transaction.id, "account_name": f"{transaction.account.name} - {transaction.account}",
                                   "date": transaction.date, "type": transaction.type, "recharge_amount": transaction.gross_total_pound})
        self.request_items_grid.options["rowData"] = recharges_list
        self.request_items_grid.update()

    async def add_transaction_to_request(self, event: nicegui.events.ClickEventArguments):
        selected_request_row = await(self.parent.ui_recharge_requests.recharge_request_grid.get_selected_row())
        if not selected_request_row:
            ui.notify("No recharge request selected")
            return 0
        selected_recharge_id = selected_request_row["id"]

        selected_transaction_rows = await(self.parent.parent.transactions.get_selected_rows())
        if not selected_transaction_rows:
            ui.notify("No transactions selected")
            return 0

        transaction_ids = [row["id"] for row in selected_transaction_rows]
        transactions = Transaction.select().where(Transaction.id.in_(transaction_ids))
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

        selected_transactions = [row["transaction_id"] for row in selected_rows]

        transactions = Transaction.select().where(Transaction.id.in_(selected_transactions))
        for transaction in transactions:
            transaction.recharge_request = None
            transaction.save()

        selected_request_row = await(self.parent.ui_recharge_requests.recharge_request_grid.get_selected_row())
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
                    self.type = ui.select(options=["Savings Plan", "Pre-pay", "Adjustment"]).classes("q-field--dense")
                    ui.label("Currency")
                    self.currency_toggle = ui.radio(["Pound", "Dollar"], value="Pound", on_change=self.change_currency).props('inline')
                    ui.label("Amount")
                    self.amount = ui.input()
                    self.exchange_rate_label = ui.label("Exchange rate (USD/GBP)")
                    self.exchange_rate = ui.input("Exchange rate")
                    ui.button("Add", on_click=self.new_transaction)
                    ui.button("Cancel", on_click=self.dialog.close)
        self.set_currency(True)

    def open(self, account_id: int):
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

        Transaction.create(account=self.selected_account_id, type=self.type.value, date=self.date_input.value,
                           amount=amount, is_pound=is_pound, _exchange_rate=exchange_rate)
        self.parent.update_transaction_grid()
        ui.notify("New transaction added.")
        self.dialog.close()

    def change_currency(self, event: nicegui.events.ValueChangeEventArguments):
        self.set_currency(bool(event.value == "Pound"))

    def set_currency(self, pound: bool):
        self.exchange_rate_label.set_visibility(not pound)
        self.exchange_rate.set_visibility(not pound)

class UINewRechargeDialog:
    def __init__(self, parent: UITransactions):
        self.parent = parent
        with ui.dialog() as self.dialog:
            with ui.card():
                ui.label("New recharge request").classes("text-2xl")
                with ui.grid(columns="auto auto"):
                    ui.label("Date")
                    self.date_input = utilities.date_picker()
                    ui.label("Reference")
                    self.reference_input = ui.input(validation={"Must provide reference": lambda value: len(value) > 1})
                    ui.button("Add", on_click=self.new_recharge_request)
                    ui.button("Cancel", on_click=self.dialog.close)

    def open(self):
        self.dialog.open()

    def close(self):
        self.dialog.close()

    def new_recharge_request(self, event: nicegui.events.ClickEventArguments):
        if self.reference_input.value != "":
            RechargeRequest.create(date=datetime.date.fromisoformat(self.date_input.value),
                                   reference=self.reference_input.value, status="Draft")
            ui.notify("New recharge request added")
            self.parent.ui_recharge_requests.populate_request_grid()
            self.close()
        else:
            ui.notify("Must provide a reference")
