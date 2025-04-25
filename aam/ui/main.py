from typing import Optional

from nicegui import ui

from aam.models import Account
from aam.ui.account_details import UIAccountDetails
from aam.ui.account_select import UIAccountSelect
from aam.ui.data_quality import UIDataQuality
from aam.ui.import_data import UIImport
from aam.ui.people import UIPeople
from aam.ui.settings import UISettings
from aam.ui.shared_charges import UISharedCharges
from aam.ui.statistics import UIStatistics
from aam.ui.transactions import UITransactions


class UIMainForm:
    def __init__(self):
        ui.page_title("AWS Account Manager")

        # Represents the ID of the organization currently selected in the UIAccountSelect gui element
        self._selected_organization_id: Optional[str] = None
        # Represents the ID of the account currently selected in the UIAccountSelect gui element
        self._selected_account_id: Optional[str] = None

        with ui.row().classes('w-full place-content-center'):
            self.account_select = UIAccountSelect(self)
        ui.separator()

        with ui.splitter(value=150).props("unit=px").classes('w-full h-full') as splitter:
            with splitter.before:
                with ui.tabs().props('vertical').classes('w-full') as tabs:
                    self.accounts_tab = ui.tab('Account Details', icon='account_circle')
                    self.transactions_tab = ui.tab('Transactions', icon='payments')
                    self.shared_charges_tab = ui.tab('Shared Charges', icon='attach_money')
                    self.import_tab = ui.tab('Import', icon='publish')
                    self.data_quality_tab = ui.tab('Data Quality', icon='verified')
                    self.stats_tab = ui.tab('Statistics', icon='query_stats')
                    self.people_tab = ui.tab('People', icon='face')
                    self.settings_tab = ui.tab('Settings', icon='settings')
            with splitter.after:
                with ui.tab_panels(tabs, value=self.accounts_tab).props('vertical').classes('w-full h-full'):
                    with ui.tab_panel(self.accounts_tab):
                        self.account_details = UIAccountDetails(self)
                    with ui.tab_panel(self.transactions_tab):
                        self.transactions = UITransactions(self)
                    with ui.tab_panel(self.shared_charges_tab):
                        self.shared_charges = UISharedCharges(self)
                    with ui.tab_panel(self.import_tab):
                        self.import_data = UIImport(self)
                    with ui.tab_panel(self.data_quality_tab):
                        self.data_quality = UIDataQuality(self)
                    with ui.tab_panel(self.stats_tab):
                        self.stats = UIStatistics(self)
                    with ui.tab_panel(self.people_tab):
                        self.people = UIPeople(self)
                    with ui.tab_panel(self.settings_tab):
                        self.settings = UISettings(self)

        # This has to be called after all UI elements are created as it references multiple elements
        self.account_select.select_default_org()

    def set_selected_organization_id(self, org_id: str | None):
        """Setter method for selected_account_id instance attribute."""
        self._selected_organization_id = org_id
        self.shared_charges.populate_shared_charges_table()
        self.account_select.update_last_updated_label(org_id)

    def get_selected_organization_id(self) -> Optional[str]:
        """Getter method for selected_account_id instance attribute."""
        return self._selected_organization_id

    def set_selected_account_id(self, account: Account | None):
        """Setter method for selected_account_id instance attribute."""
        if account:
            self._selected_account_id = account.id
        else:
            self._selected_account_id = None

    def get_selected_account_id(self) -> str | None:
        """Getter for selected_account_id instance attribute.

        The selected_account_id represents the ID of the organization currently selected in the UIAccountSelect GUI element
        """
        return self._selected_account_id

    def change_selected_account(self, account_id: str):
        """Change the account currently selected in the UIAccountSelect GUI element."""
        self.account_select.account_select.set_value(account_id)

    def change_selected_organization(self, organization_id: str | int):
        """Change the organization currently selected in the UIAccountSelect GUI element."""
        self.account_select.organization_select.set_value(organization_id)
