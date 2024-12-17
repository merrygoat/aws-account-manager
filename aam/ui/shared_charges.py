from typing import TYPE_CHECKING

import nicegui.events
from nicegui import ui

from aam.models import SharedCharge

if TYPE_CHECKING:
    from aam.main import UIMainForm


class UISharedCharges:
    def __init__(self, parent: "UIMainForm"):
        self.parent = parent

        ui.html("Shared Charges").classes("text-2xl")
        with ui.row().classes("w-full no-wrap"):
            with ui.column().classes('w-1/2'):
                self.shared_charges_table = ui.aggrid({
                    'columnDefs': [{"headerName": "id", "field": "id", "hide": True},
                                   {"headerName": "Name", "field": "name"},
                                   {"headerName": "Amount", "field": "amount"},
                                   {"headerName": "Num Accounts", "field": "recharge_amount"}],
                    'rowData': {}
                })
                self.new_charge_button = ui.button("New Shared Charge")
            with ui.column().classes('w-1/2'):
                with ui.grid(columns="auto auto"):
                    ui.label("Name").classes("place-content-center")
                    self.name = ui.input().props("outlined dense")
                    ui.label("Amount").classes("place-content-center")
                    self.amount = ui.input().props("outlined dense")
                    ui.label("Accounts").classes("place-content-center")
                    self.accounts = ui.select(options=[]).props("outlined dense")
                    self.save_changes = ui.button("Save Changes", on_click=self.save_changes)

        self.populate_shared_charges_table()

    def save_changes(self, event: nicegui.events.ClickEventArguments):
        pass

    def populate_shared_charges_table(self):
        shared_charges = SharedCharge.select()
        shared_charges = [charge.to_dict for charge in shared_charges]
        self.shared_charges_table.options["rowData"] = shared_charges
        self.shared_charges_table.update()