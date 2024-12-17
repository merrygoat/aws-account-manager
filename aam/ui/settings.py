from typing import TYPE_CHECKING

from nicegui import ui

from aam.models import Month

if TYPE_CHECKING:
    from aam.main import UIMainForm
    import nicegui.events


class UISettings:
    def __init__(self, parent: "UIMainForm"):
        self.parent = parent

        ui.label("Settings").classes("text-4xl")
        with ui.column().classes("w-full"):
            ui.label("Exchange Rate").classes("text-xl")
            self.exchange_rate_grid = UIExchangeRate(self)


class UIExchangeRate:
    def __init__(self, parent: UISettings):
        self.parent = parent

        self.month_grid = ui.aggrid({
            "defaultColDef": {"sortable": False},
            'columnDefs': [{"headerName": "id", "field": "id", "hide": True},
                           {"headerName": "Month", "field": "month", "cellDataType": "string"},
                           {"headerName": "Exchange rate £/$", "field": "exchange_rate", "editable": True}],
            'rowData': {},
            'rowSelection': 'multiple',
            'stopEditingWhenCellsLoseFocus': True,
        })
        self.month_grid.on("cellValueChanged", self.update_exchange_rate)
        self.populate_exchange_rate_grid()

    def populate_exchange_rate_grid(self):
        months = [{"id": month.id, "month": str(month), "exchange_rate": month.exchange_rate} for month in Month.select()]
        self.month_grid.options["rowData"] = months
        self.month_grid.update()

    @staticmethod
    def update_exchange_rate(event: "nicegui.events.GenericEventArguments"):
        month_id = event.args["data"]["id"]
        month = Month.get(id=month_id)
        month.exchange_rate = event.args["data"]["exchange_rate"]
        month.save()