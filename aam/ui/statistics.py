import datetime
import decimal
from typing import TYPE_CHECKING, Iterable

import nicegui.events
from nicegui import ui

import aam.utilities
from aam.models import Account, MonthlyUsage, Month

if TYPE_CHECKING:
    from aam.main import UIMainForm


class UIStatistics:
    def __init__(self, parent: "UIMainForm"):
        self.parent = parent

        ui.html("Statistics").classes("text-2xl")

        with ui.row():
            with ui.column():
                self.account_select = ui.select(label="Account", options=[], multiple=True, with_input=True).classes("min-w-[400px]").props('popup-content-class="!max-h-[500px]"')
                with ui.row():
                    self.select_all_button = ui.button("Select All", on_click=self.select_all_accounts)
                    self.select_none_button = ui.button("Select None", on_click=self.select_no_accounts)
                    self.show_active = ui.switch("Show Active", value=True, on_change=self.update_account_select_options)
                    self.show_closed = ui.switch("Show Closed", on_change=self.update_account_select_options)
                    self.show_suspended = ui.switch("Show Suspended", on_change=self.update_account_select_options)
        with ui.row():
            ui.label("Start date")
            self.start_date = aam.utilities.date_picker(datetime.date.today() - datetime.timedelta(days=90))
            ui.label("End date")
            self.end_date = aam.utilities.date_picker(datetime.date.today())
        self.calculate_usage = ui.button("Calculate Usage", on_click=self.calculate_usage)
        with ui.row():
            ui.label("Total monthly usage:")
            self.total = ui.label("£0")

        self.update_account_select_options()

    def update_account_select_options(self):
        # Have to set value to none as removing accounts from the list using one of the radio selects does not
        # remove the accounts from the value property!
        self.account_select.set_value([])
        self.total.set_text("£0")

        valid_status = []
        if self.show_active.value is True:
            valid_status.append("ACTIVE")
        if self.show_closed.value is True:
            valid_status.append("Closed")
        if self.show_suspended.value is True:
            valid_status.append("SUSPENDED")

        accounts = Account.select(Account.name, Account.id, Account.status).where((Account.status.in_(valid_status)))
        accounts = sorted(list(accounts), key=lambda item: item.name)

        account_items = {account.id: f"{account.name}" for account in accounts}
        self.account_select.set_options(account_items)
        self.account_select.update()


    def select_all_accounts(self, _event: nicegui.events.ClickEventArguments):
        self.account_select.set_value(list(self.account_select.options.keys()))
        self.account_select.update()

    def select_no_accounts(self, _event: nicegui.events.ClickEventArguments):
        self.account_select.set_value([])
        self.account_select.update()

    def calculate_usage(self, event: nicegui.events.ClickEventArguments):
        if not self.start_date.value:
            ui.notify("Must select a start date")
            return 0
        if not self.end_date.value:
            ui.notify("Must select an end date")
            return 0
        if not self.account_select.value:
            ui.notify("No account selected.")
            return 0

        start_date = datetime.date.fromisoformat(self.start_date.value)
        end_date = datetime.date.fromisoformat(self.end_date.value)

        selected_accounts = self.account_select.value

        monthly_usage: Iterable[MonthlyUsage] = (MonthlyUsage.select(MonthlyUsage, Account.id, Month.exchange_rate)
                                                .join(Account)
                                                .join_from(MonthlyUsage, Month)
                                                .where((Account.id.in_(selected_accounts) &
                                                        (MonthlyUsage.date > start_date) &
                                                        (MonthlyUsage.date < end_date))
                                                       )
                                                )
        total = decimal.Decimal(0)
        for usage in monthly_usage:
            total += usage.gross_total_pound
        self.total.set_text(f"£{total:0,.2f}")
