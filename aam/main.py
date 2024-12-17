from typing import Optional

from nicegui import ui, app

from aam import initialization
from aam.models import Account
from aam.ui.bills import UIBills
from aam.ui.import_data import UIImport
from aam.ui.settings import UISettings
from aam.ui.account_details import UIAccountDetails
from aam.ui.account_select import UIAccountSelect
from aam.ui.notes import UIAccountNotes
from aam.ui.recharges import UIRecharges
from aam.ui.people import UIPeople
from aam.ui.shared_charges import UISharedCharges

import logging
logger = logging.getLogger('peewee')
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.DEBUG)

@ui.page('/')
def main():
    initialization.initialize()

    main_form = UIMainForm()
    app.on_exception(lambda e: ui.notify(f"Exception: {e}"))
    ui.run()


class UIMainForm:
    def __init__(self):
        self._selected_account: Optional[Account] = None

        with ui.row().classes('w-full place-content-center'):
            self.account_select = UIAccountSelect(self)
        ui.separator()

        with ui.splitter(value=150).props("unit=px").classes('w-full h-full') as splitter:
            with splitter.before:
                with ui.tabs().props('vertical').classes('w-full') as tabs:
                    self.accounts_tab = ui.tab('Account Details', icon='account_circle')
                    self.bills_tab = ui.tab('Bills', icon='payments')
                    self.shared_charges_tab = ui.tab('Shared Charges', icon='attach_money')
                    self.import_tab = ui.tab('Import', icon='publish')
                    self.people_tab = ui.tab('People', icon='face')
                    self.settings_tab = ui.tab('Settings', icon='settings')
            with splitter.after:
                with ui.tab_panels(tabs, value=self.accounts_tab).props('vertical').classes('w-full h-full'):
                    with ui.tab_panel(self.accounts_tab):
                        with ui.row().classes('w-full no-wrap'):
                            with ui.column().classes('w-1/2'):
                                self.account_details = UIAccountDetails(self)
                            with ui.column().classes('w-1/2'):
                                self.notes = UIAccountNotes(self)
                    with ui.tab_panel(self.bills_tab):
                        self.bills = UIBills(self)
                        ui.separator()
                        self.recharges = UIRecharges(self)
                    with ui.tab_panel(self.shared_charges_tab):
                        self.shared_charges = UISharedCharges(self)
                    with ui.tab_panel(self.import_tab):
                        self.import_data = UIImport(self)
                    with ui.tab_panel(self.people_tab):
                        self.people = UIPeople(self)
                    with ui.tab_panel(self.settings_tab):
                        self.settings = UISettings(self)

    def set_selected_account(self, account: Account | None):
        self._selected_account = account

    def get_selected_account(self) -> Optional[Account]:
        return self._selected_account


main()
