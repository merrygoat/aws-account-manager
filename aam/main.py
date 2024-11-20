from nicegui import ui

from aam import initialization
from aam.ui.bills import UIBills
from aam.ui.settings_dialog import UISettingsDialog
from aam.ui.account_details import UIAccountDetails
from aam.ui.account_select import UIAccountSelect
from aam.ui.notes import UIAccountNotes


@ui.page('/')
def main():

    initialization.initialize()

    main_form = UIMainForm()

    ui.run()


class UIMainForm:
    def __init__(self):
        self.settings_dialog = UISettingsDialog(self)

        with ui.row().classes('w-full no-wrap'):
            self.account_grid = UIAccountSelect(self)
            ui.space()
            self.settings_button = ui.button("Settings", on_click=self.settings_dialog.open)
        ui.separator()


        with ui.row().classes('w-full no-wrap'):
            with ui.column().classes('w-1/3'):
                self.account_details = UIAccountDetails(self)
                self.notes = UIAccountNotes(self)
            with ui.column().classes('w-2/3'):
                self.bills = UIBills(self)


main()
