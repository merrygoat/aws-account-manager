import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from nicegui import ui
import nicegui.events

from aam import utilities
from aam.models import RechargeRequest, Month, Bill, Account, Person

if TYPE_CHECKING:
    from aam.main import UIMainForm


class UIRecharges:
    def __init__(self, parent: "UIMainForm"):
        self.parent = parent

        self.new_request_dialog = UINewRechargeDialog(self)

        ui.label("Recharge Requests").classes("text-4xl")
        with ui.row().classes('w-full'):
            self.request_select = ui.select(label="Recharge Request", options={}, on_change=self.request_selected).classes("min-w-[400px]").props('popup-content-class="!max-h-[500px]"')
            with ui.column():
                self.add_request_button = ui.button("Add new request", on_click=self.new_request_dialog.open)
                self.delete_selected_request_button = ui.button("Delete selected request", on_click=self.delete_selected_request)

        ui.label("Request items").classes("text-4xl")
        with ui.row().classes('w-full'):
            with ui.column().classes("w-1/2"):
                self.recharge_grid = ui.aggrid({
                    'columnDefs': [{"headerName": "bill_id", "field": "bill_id", "hide": True},
                                   {"headerName": "Account", "field": "account_name", "sort": "asc", "sortIndex": 0},
                                   {"headerName": "Month", "field": "month_date", "sort": "asc", "sortIndex": 1},
                                   {"headerName": "Amount (£)", "field": "recharge_amount", "valueFormatter": "value.toFixed(2)"}],
                    'rowData': {},
                    'rowSelection': 'multiple',
                    'stopEditingWhenCellsLoseFocus': True,
                })

            with ui.column():
                self.add_to_recharge_request_button = ui.button("Add selected bills to request", on_click=self.add_recharges)
                self.remove_recharge_button = ui.button("Remove selected items from request", on_click=self.remove_recharge_from_bill)
                self.export_recharge_button = ui.button("Export selected request", on_click=self.export_recharge_request)

        self.populate_request_select()

    async def add_recharges(self, event: nicegui.events.ClickEventArguments):
        selected_recharge_request_id = self.get_selected_recharge_request_id()
        if not selected_recharge_request_id:
            ui.notify("No recharge request selected")
            return 0

        selected_rows = await(self.parent.bills.get_selected_rows())
        if not selected_rows:
            ui.notify("No bills selected")
            return 0

        bill_ids = [row["id"] for row in selected_rows]
        bills = Bill.select().where(Bill.id.in_(bill_ids))
        for bill in bills:
            if bill.usage is None:
                ui.notify(f"Cannot add bill for month {str(bill.month)} as it has no recorded usage.")
            else:
                bill.recharge_request = selected_recharge_request_id
                bill.save()
        self.parent.bills.update_bill_grid()
        self.update_recharge_grid()

    async def remove_recharge_from_bill(self):
        selected_rows = await(self.recharge_grid.get_selected_rows())
        selected_bills = [row["bill_id"] for row in selected_rows]

        bills = Bill.select().where(Bill.id.in_(selected_bills))
        for bill in bills:
            bill.recharge_request = None
            bill.save()

        self.update_recharge_grid()
        self.parent.bills.update_bill_grid()

    def export_recharge_request(self):
        request_id = self.get_selected_recharge_request_id()
        if not request_id:
            ui.notify("No recharge request selected.")
            return 0
        bills = (Bill.select(Bill, Account, Person)
                 .join(Account)
                 .join(Person)
                 .where(Bill.recharge_request == request_id))
        if not bills:
            ui.notify("Cannot export recharge request as it has no recharges.")
            return 0

        # Group bills by account
        bill_dict = {}
        for bill in bills:
            if bill.account.id not in bill_dict:
                bill_dict[bill.account.id] = []
            bill_dict[bill.account.id].append(bill)

        export_string = "Account Number, Account Name, Budget Holder Name, Budget Holder Email, CC email, Finance Code, Task Code, Total\n"
        for account_number, bills in bill_dict.items():
            total = Decimal(0)
            for bill in bills:
                total += bill.total_pound()
            total = round(total, 2)
            account = bills[0].account
            export_string += f"{account_number}, {account.name}, {account.budget_holder.first_name}, {account.budget_holder.email}, , {account.finance_code}, {account.task_code}, {total}\n"

        recharge_request = RechargeRequest.get(id=request_id)
        ui.download(bytes(export_string, 'utf-8'), f"{recharge_request.reference} export.txt")

    def request_selected(self, event: nicegui.events.ValueChangeEventArguments):
        self.update_recharge_grid()

    def populate_request_select(self):
        requests = {request.id: f"{request.date} - {request.reference}" for request in RechargeRequest.select()}
        self.request_select.set_options(requests)

    def get_selected_recharge_request_id(self) -> Optional[int]:
        return self.request_select.value

    def update_recharge_grid(self):
        request_id = self.get_selected_recharge_request_id()
        bills = (Bill.select(Bill, Account, Month)
                     .join_from(Bill, Account)
                     .join_from(Bill, Month)
                     .where(Bill.recharge_request == request_id))
        recharges_list = []
        for bill in bills:
            recharges_list.append({"bill_id": bill.id, "account_name": f"{bill.account.name} - {bill.account}",
                                   "month_date": bill.month.to_date(), "recharge_amount": bill.total_pound()})
        self.recharge_grid.options["rowData"] = recharges_list
        self.recharge_grid.update()

    def delete_selected_request(self, event: nicegui.events.ClickEventArguments):
        request_id = self.get_selected_recharge_request_id()
        request: RechargeRequest = RechargeRequest.get(request_id)
        if request.bill:
            ui.notify("Recharge request has recharges. These must be removed before deleting the request.")
            return 0
        else:
            ui.notify(f"Request {request.reference} deleted.")
            request.delete_instance()
            self.populate_request_select()


class UINewRechargeDialog:
    def __init__(self, parent: UIRecharges):
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
            RechargeRequest.create(date=datetime.date.fromisoformat(self.date_input.value), reference=self.reference_input.value)
            ui.notify("New recharge request added")
            self.parent.populate_request_select()
            self.close()
        else:
            ui.notify("Must provide a reference")
