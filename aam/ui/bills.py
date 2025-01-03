from typing import TYPE_CHECKING

import nicegui.events
from nicegui import ui

from aam.models import Account, Bill, Month, RechargeRequest
from aam.utilities import get_months_between

if TYPE_CHECKING:
    from aam.main import UIMainForm


class UIBills:
    def __init__(self, parent: "UIMainForm"):
        self.parent = parent
        ui.label("Account Bills").classes("text-4xl")
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

    def initialize(self, account: Account | None):
        """This function is run when an account is selected from the dropdown menu."""
        if account is not None and account.creation_date:
            bills = account.get_bills()
            required_bill_months = get_months_between(account.creation_date, account.final_date())
            actual_bill_months = [bill["month_code"] for bill in bills]
            missing_months = set(required_bill_months) - set(actual_bill_months)

            if missing_months:
                for month_code in missing_months:
                    Bill.get_or_create(account=account.id, month=Month.get(month_code=month_code))
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

    async def get_selected_rows(self) -> list[dict]:
        return await(self.bill_grid.get_selected_rows())
