import calendar
import datetime
import decimal
from decimal import Decimal
from typing import TYPE_CHECKING, Iterable, Optional

import jinja2
import nicegui.events
from nicegui import ui
import requests

from aam import utilities
from aam.config import CONFIG
from aam.models import Account, RechargeRequest, Transaction, MonthlyUsage, TRANSACTION_TYPES, Note

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
                            "valueFormatter": 'value.toFixed(2)', "editable": True},
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

    async def delete_selected_transaction(self, _event: nicegui.events.ClickEventArguments):
        selected_rows = await(self.get_selected_rows())
        if selected_rows is None:
            ui.notify("No recharge request selected")

        transaction_types = [row["type"] for row in selected_rows]
        if "Monthly Usage" in transaction_types:
            ui.notify("Monthly type transactions can not be deleted.")
            return 0

        transaction_ids = [row["id"] for row in selected_rows]

        transactions = Transaction.select().where(Transaction.id.in_(transaction_ids))
        for transaction in transactions:
            transaction.delete_instance()
            self.update_transaction_grid()
            selected_request_row = await(self.ui_recharge_requests.request_grid.get_selected_row())
            if selected_request_row:
                self.ui_recharge_requests.populate_request_items_grid(selected_request_row["id"])
            ui.notify("Transaction deleted.")

    def update_transaction_grid(self):
        account_id = self.parent.get_selected_account_id()
        if account_id is None:
            row_data = []
        else:
            account: Account = Account.get(Account.id == account_id)
            row_data = account.get_transaction_details()

        self.transaction_grid.options["rowData"] = row_data
        self.transaction_grid.update()

    def update_transaction(self, event: nicegui.events.GenericEventArguments):
        """Called when the value of a cell in the transaction grid is changed."""
        if not self._validate_cell_change(event):
            return 0

        transaction_id = event.args["data"]["id"]
        transaction_type = event.args["data"]["type"]
        cell_edited = event.args["colId"]

        if transaction_type == "Monthly Usage":
            transaction: MonthlyUsage = MonthlyUsage.get(id=transaction_id)
        else:
            transaction: Transaction = Transaction.get(id=transaction_id)

        if cell_edited == "date":
            transaction.date = event.args["data"]["date"]
        elif cell_edited == "type":
            transaction.type = TRANSACTION_TYPES.index(event.args["data"]["type"])
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
        elif cell_edited == "gross_total_pound":
            if transaction.is_pound:
                transaction.amount = event.args["data"]["gross_total_pound"]
            else:
                ui.notify("Unable to edit gross amount for dollar type transactions.")
        else:
            raise TypeError(f"No method to edit '{cell_edited}' column type.")
        transaction.save()
        self.update_transaction_grid()
        ui.notify(f"Transaction {cell_edited} updated.")

    def _validate_cell_change(self, event: nicegui.events.GenericEventArguments) -> bool:
        """Validate whether a change made to the Transaction gird is valid.

        :param event: The data from the cellValueChanged AGGrid event.

        Returns True if change is valid else returns False
        """
        # Only change db as a result of callbacks triggered by user, otherwise we can get stuck in a loop.
        if "source" not in event.args:
            return False

        # Fields that cannot be edited for MonthlyUsage
        invalid_monthly_fields = ["date", "reference", "project_code", "task_code", "gross_total_pound"]
        transaction_type = event.args["data"]["type"]
        cell_edited = event.args["colId"]

        # Check whether it is valid to edit the field depending on transaction type
        invalid_change = False
        if cell_edited == "type" and event.args["oldValue"] == "Monthly Usage":
            invalid_change = True
        if cell_edited in invalid_monthly_fields and transaction_type == "Monthly Usage":
            invalid_change = True

        if invalid_change:
            ui.notify(f'Can not change field "{cell_edited}" for "Monthly Usage" type transactions.')
            self.transaction_grid.run_row_method(event.args['rowId'], 'setDataValue', cell_edited, event.args["oldValue"])
            return False

        # Check whether numeric amount is parseable
        if cell_edited in ["amount", "gross_total_pound"] and event.args["newValue"] is not None:
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
                               {"headerName": "Start Date", "field": "start_date", "sort": "asc", "sortIndex": 0},
                               {"headerName": "End Date", "field": "end_date", "sort": "asc", "sortIndex": 0},
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
                self.export_selected_request_button = ui.button("Export selected request", on_click=self.export_recharge_request)

        with ui.column().classes("w-1/3"):
            ui.label("Request items").classes("text-4xl")
            self.request_items_grid = ui.aggrid({
                'columnDefs': [{"headerName": "account_id", "field": "account_id", "hide": True},
                               {"headerName": "transaction_ids", "field": "transaction_ids", "hide": True},
                               {"headerName": "Account", "field": "account_name", "sort": "asc", "sortIndex": 0},
                               {"headerName": "Num Transactions", "field": "num_transactions"},
                               {"headerName": "Start balance", "field": "start_balance",
                                "valueFormatter": 'value.toFixed(2)'},
                               {"headerName": "Transaction Total", "field": "transaction_total",
                                "valueFormatter": 'value.toFixed(2)'},
                               {"headerName": "End balance", "field": "end_balance",
                                "valueFormatter": 'value.toFixed(2)'},
                               ],
                'rowData': {},
                'rowSelection': 'multiple',
                'stopEditingWhenCellsLoseFocus': True,
            })

        with ui.column().classes("w-1/3"):
            ui.label("Email body").classes("text-4xl")
            with ui.grid(columns="auto 1fr").classes('w-full'):
                ui.label("To:")
                self.email_to = ui.input()
                ui.label("CC:")
                self.email_cc = ui.input()
                ui.label("Subject:")
                self.email_subject = ui.input("")
            self.email_body = ui.textarea().classes("w-full").props("input-class=h-96")
            with ui.row():
                self.send_email_button = ui.button("Send email", on_click=self.send_email)
                self.email_spinner = ui.spinner(size='lg')

        self.request_grid.on('rowSelected', self.request_selected)
        self.request_grid.on('cellValueChanged', self.request_edited)
        self.populate_request_grid()
        self.request_items_grid.on("cellClicked", self.request_item_cell_clicked)
        self.request_items_grid.on("cellDoubleClicked", self.request_item_cell_double_clicked)
        self.email_spinner.visible = False

    async def get_selected_recharge_id(self) -> Optional[str]:
        """Get the ID of the selected RechargeRequest."""
        selected_row = await(self.request_grid.get_selected_row())
        if selected_row is None:
            return None
        return selected_row["id"]

    async def get_selected_request_item_account(self) -> Optional[str]:
        """Get the ID of the Account corresponding to the selected RechargeRequest item."""
        selected_row = await(self.request_items_grid.get_selected_row())
        if selected_row is None:
            return None
        return selected_row["account_id"]

    def request_selected(self, event: nicegui.events.GenericEventArguments):
        """Populate the request item table. Triggered by selection of a row in the RechargeRequest table."""
        if event.args["selected"] is True:
            self.populate_request_items_grid(event.args["data"]["id"])

    @staticmethod
    def request_edited(event: nicegui.events.GenericEventArguments):
        """Save changes to a RechargeRequest after it is edited in the RechargeRequest table."""
        request_id = event.args["data"]["id"]
        request = RechargeRequest.get(id=request_id)
        request.status = event.args["data"]["status"]
        request.reference = event.args["data"]["reference"]
        request.save()

    def populate_request_grid(self):
        recharge_requests: Iterable[RechargeRequest] = RechargeRequest.select()
        request_details = [request.to_json() for request in recharge_requests]
        self.request_grid.options["rowData"] = request_details
        self.request_grid.update()

    async def delete_selected_request(self, _event: nicegui.events.ClickEventArguments):
        selected_row = await(self.request_grid.get_selected_row())
        if selected_row is None:
            ui.notify("No recharge request selected to delete.")
            return 0
        request: RechargeRequest = RechargeRequest.get(selected_row["id"])

        transactions = Transaction.select().where(Transaction.recharge_request == request)
        for transaction in transactions:
            transaction.recharge_request = None
            transaction.save()

        usage: Iterable[MonthlyUsage] = MonthlyUsage.select().where(MonthlyUsage.recharge_request == request)
        for month in usage:
            month.recharge_request = None
            month.save()

        request.delete_instance()
        ui.notify(f"Request {request.reference} deleted.")
        self.populate_request_grid()
        self.populate_request_items_grid(None)

    async def export_recharge_request(self):
        """Export data for the accounts that are to be recharged."""
        selected_row = await(self.request_grid.get_selected_row())
        if selected_row is None:
            ui.notify("No recharge request selected to export.")
            return 0

        request_id = selected_row["id"]
        recharge_request: RechargeRequest = RechargeRequest.get(id=request_id)

        recharge_items = self.request_items_grid.options['rowData']
        if not recharge_items:
            ui.notify("Cannot export recharge request as it has no recharges.")
            return 0

        # Put items into dict by account id
        item_dict = {item["account_id"]: item for item in recharge_items}

        # Get the finance codes for each item
        account_ids = list(item_dict.keys())
        codes = Account.select(Account.id, Account.finance_code, Account.task_code).where(Account.id.in_(account_ids)).dicts()
        for account in codes:
            item_dict[account["id"]]["finance_code"] = account["finance_code"]
            item_dict[account["id"]]["task_code"] = account["task_code"]

        recharge_string = self.generate_recharge_string(item_dict)
        ui.download(bytes(recharge_string, 'utf-8'), f"{recharge_request.reference} export.txt", "text/plain")

    @staticmethod
    def generate_recharge_string(request_items: dict[str: dict]):
        """Generate a string to be exported as a CSV to submit for journal transfer."""
        export_string = "Account Name, Finance Code, Task Code, Total\n"
        for account_id, row in request_items.items():
            export_string += f"{row['account_name']}, {row["finance_code"]}, {row["task_code"]}, {round(row["end_balance"], 2)}\n"
        return export_string

    @staticmethod
    def generate_recharge_email(transactions: list[Transaction | MonthlyUsage], recharge_request: RechargeRequest) -> str:
        """Use Jinja to generate the body of the email to send to the customer from a template."""
        account = transactions[0].account
        if account.budget_holder is None:
            ui.notify(f'Error for account "{account.name}" - no budget holder recorded.')
            return ""
        data = {"first_name": account.budget_holder.first_name,
                "account_name": account.name,
                "account_id": account.id,
                "recharge_quarter": "4",
                "recharge_year": "2024",
                "start_balance": account.get_balance(recharge_request.start_date, inclusive=False),
                "transactions": [],
                "end_balance": account.get_balance(recharge_request.end_date),
                "finance_code": account.finance_code,
                "task_code": account.task_code,
                "recharge_start_date": recharge_request.start_date,
                "recharge_end_date": recharge_request.end_date,
                "recharge_date": (datetime.date.today() + datetime.timedelta(days=14)).strftime("%d/%m/%y")}
        for transaction in transactions:
            data["transactions"].append({"date": transaction.date, "type": TRANSACTION_TYPES[transaction.type],
                                         "amount": transaction.gross_total_pound, "note": transaction.note})
        env = jinja2.Environment(loader=jinja2.PackageLoader("aam"), undefined=jinja2.StrictUndefined)
        template = env.get_template("email_base.jinja")
        return template.render(data=data)

    async def send_email(self):
        """Email a customer and add a Note to the Account with the content of the email."""
        self.email_spinner.visible = True
        account_id = await(self.get_selected_request_item_account())
        to = self.email_to.value
        cc = self.email_cc.value
        subject = self.email_subject.value
        body: str = self.email_body.value
        html_body = body.replace("\n", "<br>")
        payload = {"to": to, "cc": cc, "subject": subject, "body": html_body}
        response = requests.post(CONFIG["email_url"], json=payload)
        note_text = f"to: {to}\ncc:{cc}\nsubject: {subject}\n\n{body}"
        Note.create(date=datetime.date.today(), text=note_text, type="Sent email", account=account_id)
        self.email_spinner.visible = False
        ui.notify(f"Email request response status code: {response.status_code}")

    async def request_item_cell_clicked(self, event: nicegui.events.GenericEventArguments):
        account_id = event.args["data"]["account_id"]
        recharge_id = await(self.get_selected_recharge_id())
        recharge_request: RechargeRequest = RechargeRequest.get(recharge_id)
        transactions = recharge_request.get_transactions(account_id)
        email_body = self.generate_recharge_email(transactions, recharge_request)

        self.email_to.set_value(transactions[0].account.budget_holder.email)
        self.email_cc.set_value("")
        self.email_subject.set_value(f"Research IT AWS account recharge - {transactions[0].account.name}")
        self.email_body.set_value(email_body)


    def request_item_cell_double_clicked(self, event: nicegui.events.GenericEventArguments):
        account: Account = Account.get(Account.id == event.args["data"]["account_id"])
        self.parent.parent.change_selected_organization(account.organization_id)
        self.parent.parent.change_selected_account(account.id)

    def populate_request_items_grid(self, request_id: int | None):
        if request_id is None:
            accounts = []
        else:
            request = RechargeRequest.get(RechargeRequest.id == request_id)

            transactions: Iterable[Transaction] = (Transaction.select(Transaction, Account)
                                                   .join(Account)
                                                   .where(Transaction.recharge_request == request_id))
            monthly_usage: Iterable[MonthlyUsage] = (MonthlyUsage.select(MonthlyUsage, Account)
                                             .join(Account)
                                             .where(MonthlyUsage.recharge_request == request_id))

            # For the properties exposed in the grid we can treat Transactions and MonthlyUsage as the same type of object.
            items = list(transactions)
            items.extend(list(monthly_usage))

            accounts = {}

            for item in items:
                account_id = item.account.id
                if account_id not in accounts:
                    start_balance = item.account.get_balance(request.start_date, inclusive=False)
                    end_balance = item.account.get_balance(request.end_date, inclusive=False)
                    accounts[account_id] = {"account_name": item.account.name, "account_id": account_id,
                                            "transaction_total": 0, "num_transactions": 0,
                                            "start_balance": start_balance, "end_balance": end_balance}
                accounts[account_id]["transaction_total"] += item.gross_total_pound
                accounts[account_id]["num_transactions"] += 1

            # Unpack dict to list to display in grid
            accounts = [value for value in accounts.values()]

        self.request_items_grid.options["rowData"] = accounts
        self.request_items_grid.update()

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
    """Dialog box with options allowing the user to create a new RechargeRequest."""

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

    def open(self):
        self.dialog.open()

    def close(self):
        self.dialog.close()

    def new_recharge_request(self, _event: nicegui.events.ClickEventArguments):
        """Get the information the user has input to the Dialog and use it to create a new RechargeRequest."""
        start_date = datetime.date(self.start_year.value, self.start_month.value, 1)
        last_day = calendar.monthrange(self.end_year.value, self.end_month.value)[1]
        end_date = datetime.date(self.end_year.value, self.end_month.value, last_day)

        if end_date < start_date:
            ui.notify("End month must be after start month.")
            return 0

        if self.reference_input.value != "":
            recharge_request = RechargeRequest.create(start_date=start_date, end_date=end_date,
                                                      reference=self.reference_input.value, status="Draft")
        else:
            ui.notify("Must provide a reference")
            return 0

        self.add_transactions_to_request(start_date, end_date, recharge_request)

        ui.notify("New recharge request added")
        self.parent.parent.ui_recharge_requests.populate_request_grid()
        self.close()

    @staticmethod
    def add_transactions_to_request(start_date: datetime.date, end_date: datetime.date,
                                    recharge_request: RechargeRequest):
        """Find any Transaction or MonthlyUsage between `start_date` and the `end_date` and add them to the
        recharge request."""

        transactions: Iterable[Transaction] = (Transaction.select(Transaction, Account)
                                               .join(Account)
                                               .where((Account.is_recharged == True) & (Transaction.date >= start_date) & (Transaction.date < end_date)))
        for transaction in transactions:
            if not transaction.recharge_request:
                transaction.recharge_request = recharge_request.id
                transaction.save()
            else:
                ui.notify(
                    f"Transaction for account: {transaction.account.name}, date: {transaction.date} is already assigned to another recharge.")

        usage = (MonthlyUsage.select(MonthlyUsage, Account)
                 .join(Account)
                 .where((Account.is_recharged == True) & (MonthlyUsage.date >= start_date) & (MonthlyUsage.date <= end_date)))
        for month_usage in usage:
            if not month_usage.recharge_request:
                month_usage.recharge_request = recharge_request.id
                month_usage.save()
            else:
                ui.notify(
                    f"MonthlyUsage for account: {month_usage.account.name}, date: {month_usage.date} is already assigned to another recharge.")
