from typing import Optional, TYPE_CHECKING

import nicegui.events
from nicegui import ui

from aam.models import Account, Bill, Month
from aam.utilities import get_bill_months

if TYPE_CHECKING:
    from aam.main import UIMainForm


class UIBills:
    def __init__(self, parent: "UIMainForm"):
        self.parent = parent
        ui.html("Money").classes("text-2xl")
        self.bill_grid = ui.aggrid({
            'columnDefs': [{"headerName": "id", "field": "id", "hide": True},
                           {"headerName": "Month", "field": "month", "sort": "desc"},
                           {"headerName": "Usage ($)", "field": "usage_dollar", "editable": True,
                            "valueFormatter": "value.toFixed(2)"},
                           {"headerName": "Support Charge ($)", "field": "support_charge",
                            "valueFormatter": "value.toFixed(2)"},
                           {"headerName": "Total (£)", "field": "total_pound",
                            "valueFormatter": "value.toFixed(2)"}],
            'rowData': {},
            'rowSelection': 'multiple',
            'stopEditingWhenCellsLoseFocus': True,
        })
        self.bill_grid.on("cellValueChanged", self.update_bill)

    def initialize(self, account: Account):
        """This function is run when an account is selected from the dropdown menu."""
        if account.creation_date:
            bills = account.get_bills()
            required_bill_months = get_bill_months(account.creation_date, account.final_date())
            actual_bill_months = [bill["month"] for bill in bills]
            missing_months = set(required_bill_months) - set(actual_bill_months)

            if missing_months:
                for month in missing_months:
                    Bill.get_or_create(account_id=account.id, month_id=Month.get(date=month))
                bills = account.get_bills()
            self.bill_grid.options["rowData"] = bills
        else:
            self.bill_grid.options["rowData"] = {}
        self.bill_grid.update()

    def update_grid(self):
        bills = self.parent.get_selected_account().get_bills()
        self.bill_grid.options["rowData"] = bills
        self.bill_grid.update()

    def update_bill(self, event: nicegui.events.GenericEventArguments):
        bill_id = event.args["data"]["id"]
        bill = Bill.get(id=bill_id)
        bill.usage = event.args["data"]["usage_dollar"]
        bill.save()
        self.update_grid()
