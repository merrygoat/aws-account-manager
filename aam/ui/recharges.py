from typing import TYPE_CHECKING

from nicegui import ui

from aam.models import Recharge

if TYPE_CHECKING:
    from aam.main import UIMainForm


class UIRecharges:
    def __init__(self, parent: "UIMainForm"):
        self.parent = parent

        ui.label("Recharges").classes("text-4xl")

        self.recharge_grid = ui.aggrid({
            'columnDefs': [{"headerName": "id", "field": "id", "hide": True},
                           {"headerName": "Quarter", "field": "quarter", "sort": "desc"}
                           ],
            'rowData': {},
            'rowSelection': 'multiple',
            'stopEditingWhenCellsLoseFocus': True,
        })

        self.update_recharge_grid()

    def update_recharge_grid(self):
        pass
