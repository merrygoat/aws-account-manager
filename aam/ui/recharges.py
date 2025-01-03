import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from nicegui import ui
import nicegui.events

from aam import utilities
from aam.models import RechargeRequest, Month, Recharge, Bill, Account, Person

if TYPE_CHECKING:
    from aam.main import UIMainForm


class UIRecharges:
    def __init__(self, parent: "UIMainForm"):
        self.parent = parent

        self.new_request_dialog = UINewRechargeDialog(self)

        ui.label("Recharges").classes("text-4xl")

        with ui.row():
            self.request_select = ui.select(label="Recharge Request", options={}, on_change=self.request_selected).classes(
                "min-w-[400px]").props('popup-content-class="!max-h-[500px]"')
            self.add_request_button = ui.button("Add new request", on_click=self.new_request_dialog.open)
            self.delete_selected_request_button = ui.button("Delete selected request", on_click=self.delete_selected_request)

        self.recharge_grid = ui.aggrid({
            'columnDefs': [{"headerName": "id", "field": "id", "hide": True},
                           {"headerName": "Account", "field": "account_name", "sort": "asc", "sortIndex": 0},
                           {"headerName": "Month", "field": "month_date", "sort": "asc", "sortIndex": 1},
                           {"headerName": "Amount (£)", "field": "recharge_amount", "valueFormatter": "value.toFixed(2)"}],
            'rowData': {},
            'rowSelection': 'multiple',
            'stopEditingWhenCellsLoseFocus': True,
        })

        self.remove_recharge_button = ui.button("Remove selected items from request", on_click=self.remove_recharge_from_request)
        self.export_recharge_button = ui.button("Export selected request", on_click=self.export_recharge_request)
        self.populate_request_select()

    def export_recharge_request(self):
        request_id = self.get_selected_recharge_request_id()
        if not request_id:
            ui.notify("No recharge request selected.")
            return 0
        recharge_request = RechargeRequest.get(RechargeRequest.id == request_id)
        recharges = (Recharge.select(Recharge, Month, Bill, Account)
                     .join(Month)
                     .join(Bill, on=((Month.id == Bill.month) & (Recharge.account == Bill.account_id)))
                     .join(Account)
                     .join(Person)
                     .where(Recharge.recharge_request == request_id))

        recharge_dict = {}
        for recharge in recharges:
            if recharge.account.id not in recharge_dict:
                recharge_dict[recharge.account.id] = []
            recharge_dict[recharge.account.id].append(recharge)

        export_string = "Account Number, Account Name, Budget Holder Name, Budget Holder Email, CC email, Finance Code, Task Code, Total\n"
        for account_number, recharges in recharge_dict.items():
            total = Decimal(0)
            for recharge in recharges:
                total += recharge.month.bill.total_pound()
            total = round(total, 2)
            account = recharges[0].account
            export_string += f"{account_number}, {account.name}, {account.budget_holder.first_name}, {account.budget_holder.email}, , {account.finance_code}, {account.task_code}, {total}\n"
        ui.download(bytes(export_string, 'utf-8'), f"{recharge_request.reference} export.txt")

    async def remove_recharge_from_request(self):
        selected_rows = await(self.recharge_grid.get_selected_rows())
        selected_recharges = [row["id"] for row in selected_rows]
        delete_query = Recharge.delete().where(Recharge.id.in_(selected_recharges))
        delete_query.execute()
        self.update_recharge_grid()
        self.parent.bills.update_bill_grid()

    def request_selected(self, event: nicegui.events.ValueChangeEventArguments):
        self.update_recharge_grid()

    def populate_request_select(self):
        requests = {request.id: f"{request.date} - {request.reference}" for request in RechargeRequest.select()}
        self.request_select.set_options(requests)

    def get_selected_recharge_request_id(self) -> Optional[int]:
        return self.request_select.value

    def update_recharge_grid(self):
        request_id = self.get_selected_recharge_request_id()
        recharges = (Recharge.select(Recharge, Month, Bill, Account)
                     .join(Month)
                     .join(Bill, on=((Month.id == Bill.month) & (Recharge.account == Bill.account_id)))
                     .join(Account)
                     .where(Recharge.recharge_request == request_id))
        recharges_list = []
        for recharge in recharges:
            recharges_list.append({"id": recharge.id, "account_name": f"{recharge.month.bill.account_id.name} - {recharge.account_id}",
                                   "month_date": recharge.month.to_date(), "recharge_amount": recharge.month.bill.total_pound()})
        self.recharge_grid.options["rowData"] = recharges_list
        self.recharge_grid.update()

    def delete_selected_request(self, event: nicegui.events.ClickEventArguments):
        request_id = self.get_selected_recharge_request_id()
        request: RechargeRequest = RechargeRequest.get(request_id)
        if request.recharges:
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
