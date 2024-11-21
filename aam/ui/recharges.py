import datetime
from typing import TYPE_CHECKING, Optional

from nicegui import ui
import nicegui.events

from aam import utilities
from aam.models import RechargeRequest

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

        self.recharge_grid_title = ui.label("Recharges in recharge request: ")
        self.recharge_grid = ui.aggrid({
            'columnDefs': [{"headerName": "id", "field": "id", "hide": True},
                           {"headerName": "Account", "field": "account_id"},
                           {"headerName": "Month", "field": "month_id"},
                           {"headerName": "Amount", "field": "recharge_amount"}],
            'rowData': {},
            'rowSelection': 'multiple',
            'stopEditingWhenCellsLoseFocus': True,
        })

        self.get_request_options()

    def request_selected(self, event: nicegui.events.ValueChangeEventArguments):
        request_id = event.sender.value
        request = RechargeRequest.get(RechargeRequest.id == request_id)
        self.recharge_grid_title.text = f"Recharges in recharge request: {request.reference}"
        self.update_recharge_grid()

    def get_request_options(self):
        requests = {request.id: f"{request.date} - {request.reference}" for request in RechargeRequest.select()}
        self.request_select.set_options(requests)

    def get_selected_recharge_request(self) -> Optional[RechargeRequest]:
        request_id = self.request_select.value
        if request_id:
            return RechargeRequest.get(RechargeRequest.id == request_id)
        else:
            return None

    def update_recharge_grid(self):
        request = self.get_selected_recharge_request()
        recharges = [{"id": recharge.id, "account_id": recharge.account.id, "month_id": recharge.month.date.isoformat(), "recharge_amount": ""} for recharge in request.recharges]
        self.recharge_grid.options["rowData"] = recharges
        self.recharge_grid.update()

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
            self.parent.get_request_options()
            self.close()
        else:
            ui.notify("Must provide a reference")
