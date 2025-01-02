from typing import TYPE_CHECKING

import nicegui.events
from nicegui import ui

from aam.models import Account, Bill, Month, RechargeRequest, Recharge
from aam.utilities import get_months_between

if TYPE_CHECKING:
    from aam.main import UIMainForm


class UIBills:
    def __init__(self, parent: "UIMainForm"):
        self.parent = parent
        ui.html("Money").classes("text-2xl")
        self.bill_grid = ui.aggrid({
            'defaultColDef': {"suppressMovable": True},
            'columnDefs': [{"headerName": "id", "field": "id", "hide": True},
                           {"headerName": "Month", "field": "month_date", "sort": "asc"},
                           {"headerName": "Usage ($)", "field": "usage_dollar", "editable": True,
                            "valueFormatter": "value.toFixed(2)"},
                           {"headerName": "Support Charge ($)", "field": "support_charge",
                            "valueFormatter": "value.toFixed(2)"},
                           {"headerName": "Shared Charges ($)", "field": "shared_charges",
                            "valueFormatter": "value.toFixed(2)"},
                           {"headerName": "Total ($)", "field": "total_dollar",
                            "valueFormatter": "value.toFixed(2)"},
                           {"headerName": "Total (£)", "field": "total_pound",
                            "valueFormatter": "value.toFixed(2)"},
                           {"headerName": "Recharge Reference", "field": "recharge_reference"}],
            'rowData': {},
            'rowSelection': 'multiple',
            'stopEditingWhenCellsLoseFocus': True,
        })
        self.bill_grid.on("cellValueChanged", self.update_bill)
        self.add_to_recharge_request_button = ui.button("Add selected bills to selected recharge request", on_click=self.add_recharges)

    def initialize(self, account: Account | None):
        """This function is run when an account is selected from the dropdown menu."""
        if account is None:
            return 0
        if account.creation_date:
            bills = account.get_bills()
            required_bill_months = get_months_between(account.creation_date, account.final_date())
            actual_bill_months = [bill["month_code"] for bill in bills]
            missing_months = set(required_bill_months) - set(actual_bill_months)

            if missing_months:
                for month_code in missing_months:
                    Bill.get_or_create(account_id=account.id, month_id=Month.get(month_code=month_code))
                bills = account.get_bills()
            self.bill_grid.options["rowData"] = bills
        else:
            self.bill_grid.options["rowData"] = {}
        self.bill_grid.update()

    def update_bill_grid(self):
        account = self.parent.get_selected_account()
        if account is None:
            row_data = []
        else:
            row_data = account.get_bills()
        self.bill_grid.options["rowData"] = row_data
        self.bill_grid.update()

    def update_bill(self, event: nicegui.events.GenericEventArguments):
        bill_id = event.args["data"]["id"]
        bill = Bill.get(id=bill_id)
        bill.usage = event.args["data"]["usage_dollar"]
        bill.save()
        self.update_bill_grid()

    async def add_recharges(self, event: nicegui.events.ClickEventArguments):
        selected_recharge_request_id: RechargeRequest = self.parent.recharges.get_selected_recharge_request_id()
        if not selected_recharge_request_id:
            ui.notify("No recharge request selected")
            return 0

        selected_rows = await(self.bill_grid.get_selected_rows())
        if not selected_rows:
            ui.notify("No bills selected")
            return 0

        bill_ids = [row["id"] for row in selected_rows]
        bills = Bill.select().where(Bill.id.in_(bill_ids))
        for bill in bills:
            if bill.usage is None:
                ui.notify(f"Cannot add bill for month {str(bill.month)} as it has no recorded usage.")
            else:
                Recharge.get_or_create(account_id=bill.account_id, month=bill.month.id, recharge_request=selected_recharge_request_id)
        self.update_bill_grid()
        self.parent.recharges.update_recharge_grid()
