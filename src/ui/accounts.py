import time
from datetime import date
from itertools import zip_longest
from pathlib import Path
from typing import Literal, Type

import flet as ft

from src.core import (
    Farmer,
    SessionNotCreatedException,
    WebDriverException,
    accountStatus,
)


class AccountsContainer(ft.UserControl):
    def __init__(self, page: ft.Page, accounts_page):
        super().__init__()
        self.page = page
        self.accounts_page: Type[Accounts] = accounts_page
        self.is_browser_running: bool = False
        self.accounts_path = Path(
            page.client_storage.get('MRFarmer.accounts_path')
        )
        self.container = ft.Container(expand=True)
        self.no_result = ft.Row(
            [
                ft.Text(
                    'Nothing to show based on your search/filter',
                    expand=True,
                    text_align='center',
                    font_family='SF regular',
                    size=18,
                )
            ]
        )
        self.was_filtered: bool = False
        self.filtered_accounts: list = None

    def get_cards(self, accounts: list) -> ft.Column:
        list_of_cards = []
        divided_accounts_lists = self.divide_accounts_into_lists(accounts)
        column = ft.Column(expand=True)
        for accounts in divided_accounts_lists:
            cards = [
                AccountCard(
                    account, self.page, self.accounts_page, self.accounts_path
                ).card
                for account in accounts
                if account is not None
            ]
            list_of_cards.append(cards)

        for _list in list_of_cards:
            row = ft.Row(controls=_list)
            column.controls.append(row)
        return column

    def divide_accounts_into_lists(self, accounts: list) -> list:
        return list(zip_longest(*[iter(accounts)] * 2, fillvalue=None))

    def build(self) -> ft.Container:
        if self.page.session.contains_key('MRFarmer.accounts'):
            accounts = self.page.session.get('MRFarmer.accounts')
            self.accounts_page.control_bar.visible = True
            column = self.get_cards(accounts)
            self.container.content = column
        return self.container

    def display_no_result(self):
        self.container.content = self.no_result
        self.container.update()
        self.page.update()

    def refresh(self):
        if self.was_filtered and self.filtered_accounts is not None:
            accounts = self.filtered_accounts
        else:
            accounts = self.page.session.get('MRFarmer.accounts')
        if accounts is not None:
            column = self.get_cards(accounts)
            self.container.content = column
            # self.container.update()
            self.page.update()
        else:
            self.accounts_page.no_accounts_description.visible = True
            self.page.update()

    def _filter(self, by):
        accounts = self.page.session.get('MRFarmer.accounts')
        self.accounts_page.search_field.value = ''
        if by == 'Farmed':
            filtered_accounts = list(
                filter(
                    lambda account: account['log']['Last check']
                    == str(date.today())
                    and account['log']['Status'] == accountStatus.FARMED,
                    accounts,
                )
            )
        elif by == 'Locked':
            filtered_accounts = list(
                filter(
                    lambda account: account['log']['Status']
                    == accountStatus.LOCKED,
                    accounts,
                )
            )
        elif by == 'Suspended':
            filtered_accounts = list(
                filter(
                    lambda account: account['log']['Status']
                    == accountStatus.SUSPENDED,
                    accounts,
                )
            )
        elif by == 'Accounts with error':
            filtered_accounts = list(
                filter(
                    lambda account: account['log']['Status']
                    in (
                        accountStatus.ERROR,
                        accountStatus.SEARCH_WORDS_ERROR,
                        accountStatus.UNUSUAL_ACTIVITY,
                        accountStatus.PC_LOGIN_FAILED,
                        accountStatus.MOBILE_LOGIN_FAILED,
                    ),
                    accounts,
                )
            )
        elif by == '0 < Points <5000':
            filtered_accounts = list(
                filter(
                    lambda account: account['log'].get('Points', 0)
                    in range(5001),
                    accounts,
                )
            )
        elif by == '5000 < Points < 10000':
            filtered_accounts = list(
                filter(
                    lambda account: account['log'].get('Points', 0)
                    in range(5000, 10001),
                    accounts,
                )
            )
        elif by == '10000 < Points < 15000':
            filtered_accounts = list(
                filter(
                    lambda account: account['log'].get('Points', 0)
                    in range(10000, 15001),
                    accounts,
                )
            )
        elif by == '15000 < Points':
            filtered_accounts = list(
                filter(
                    lambda account: account['log'].get('Points', 0) > 15000,
                    accounts,
                )
            )
        elif by == 'All':
            self.accounts_page.search_field.value = ''
            self.was_filtered = False
            self.filtered_accounts = None
            self.refresh()
            return
        if len(filtered_accounts) == 0:
            self.display_no_result()
            return
        else:
            self.was_filtered = True
            self.filtered_accounts = filtered_accounts
            column = self.get_cards(filtered_accounts)
            self.container.content = column
            self.container.update()
            self.page.update()

    def search(self, query: str):
        if query == '' or query is None:
            self.refresh()
            return
        self.accounts_page.filter_by.value = 'All'
        accounts = self.page.session.get('MRFarmer.accounts')
        filtered_accounts = list(
            filter(
                lambda account: query.lower() in account['username'].lower(),
                accounts,
            )
        )
        if len(filtered_accounts) == 0:
            self.display_no_result()
            return
        else:
            self.was_filtered = True
            self.filtered_accounts = filtered_accounts
            column = self.get_cards(filtered_accounts)
            self.container.content = column
            self.container.update()
            self.page.update()

    def clear_search(self, e: ft.ControlEvent):
        self.accounts_page.search_field.value = ''
        self.accounts_page.filter_by.value = 'All'
        self.was_filtered = False
        self.filtered_accounts = None
        self.refresh()


class AccountCard:
    def __init__(
        self, account: dict, page: ft.Page, accounts_page, accounts_path: Path
    ):
        self.account = account
        self.page = page
        self.accounts_path = accounts_path
        self.accounts_page: Type[Accounts] = accounts_page
        self.card_creator()
        self.set_tint_on_card()

    def card_creator(self):
        popup_items = [
            ft.PopupMenuItem(
                text='Copy Email',
                icon=ft.icons.COPY,
                on_click=lambda _: self.page.set_clipboard(
                    self.account['username']
                ),
            ),
            ft.PopupMenuItem(
                text='Copy password',
                icon=ft.icons.COPY,
                on_click=lambda _: self.page.set_clipboard(
                    self.account['password']
                ),
            ),
            ft.PopupMenuItem(),
            ft.PopupMenuItem(
                text='Reset log',
                icon=ft.icons.RESTART_ALT,
                on_click=lambda _: self.accounts_page.clear_account_log(
                    self.account['username']
                ),
            ),
            ft.PopupMenuItem(
                text='Set as finished',
                icon=ft.icons.DONE,
                on_click=lambda _: self.accounts_page.set_account_to_finished(
                    self.account['username']
                ),
            ),
            ft.PopupMenuItem(),
            ft.PopupMenuItem(
                text='Edit account',
                icon=ft.icons.EDIT,
                on_click=lambda e: self.accounts_page.set_value_to_fields(
                    e, self.account
                ),
            ),
            ft.PopupMenuItem(
                text='Delete account',
                icon=ft.icons.DELETE,
                on_click=lambda _: self.accounts_page.open_delete_dialog(
                    self.account['username']
                ),
            ),
        ]
        if self.is_session_exist():
            popup_items.append(ft.PopupMenuItem())
            popup_items.append(
                ft.PopupMenuItem(
                    text='Session browser',
                    icon=ft.icons.OPEN_IN_BROWSER,
                    on_click=lambda _: self.accounts_page.open_session_browser(
                        self.account
                    ),
                )
            )

        self.card = ft.Card(
            expand=4,
            elevation=3.5,
            content=ft.Container(
                margin=ft.margin.all(15),
                content=ft.Column(
                    expand=3,
                    controls=[
                        ft.ListTile(
                            title=ft.Text(
                                self.account['username'].capitalize(), size=14
                            ),
                            leading=self.get_icon(),
                            subtitle=ft.Text(
                                self.get_subtitle(), font_family='SF light'
                            ),
                            trailing=ft.PopupMenuButton(
                                icon=ft.icons.MORE_VERT, items=popup_items
                            ),
                        ),
                        ft.Row(
                            [
                                ft.Text(
                                    'Earned points: {earned_points}'.format(
                                        earned_points=self.account.get(
                                            'log'
                                        ).get("Today's points")
                                    ),
                                    font_family='SF regular',
                                )
                            ]
                        ),
                        ft.Row(
                            [
                                ft.Text(
                                    f"Total points: {self.account.get('log').get('Points')}",
                                    font_family='SF regular',
                                )
                            ]
                        ),
                    ],
                ),
            ),
        )

    def is_farmed(self):
        if (
            self.account['log']['Last check'] == str(date.today())
            and self.account['log'].get('Status', 'Not farmed')
            == accountStatus.FARMED
        ):
            return True
        return False

    def get_icon(self):
        last_check = self.account['log']['Last check']
        if self.is_farmed():
            return ft.Icon(ft.icons.CHECK, color='green')
        elif (
            self.account['log'].get('Status', last_check)
            == accountStatus.SUSPENDED
        ):
            return ft.Icon(ft.icons.BLOCK, color='red')
        elif (
            self.account['log'].get('Status', last_check)
            == accountStatus.LOCKED
        ):
            return ft.Icon(ft.icons.LOCK, color=ft.colors.AMBER_500)
        elif (
            self.account['log'].get('Status', last_check)
            == accountStatus.UNUSUAL_ACTIVITY
        ):
            return ft.Icon(ft.icons.WARNING, color=ft.colors.AMBER_500)
        elif self.account['log'].get('Status', last_check) in (
            accountStatus.SEARCH_WORDS_ERROR,
            accountStatus.ERROR,
            accountStatus.PC_LOGIN_FAILED,
            accountStatus.MOBILE_LOGIN_FAILED,
            accountStatus.PROXY_DEAD,
        ):
            return ft.Icon(ft.icons.ERROR, color=ft.colors.AMBER_500)
        else:
            return ft.Icon(ft.icons.ACCOUNT_CIRCLE)

    def is_session_exist(self):
        if Path(
            f"{self.accounts_path.parent}/Profiles/{self.account['username']}/PC"
        ).exists():
            return True
        return False

    def get_subtitle(self):
        last_check = self.account['log']['Last check']
        if 'Status' in self.account['log'].keys():
            if self.is_farmed():
                return f"{self.account['log']['Last check']} | {self.account['log'].get('Status', accountStatus.NOT_FARMED)}"
            elif (
                self.account['log'].get('Status', last_check)
                == accountStatus.SUSPENDED
            ):
                return 'Your account has been suspended'
            elif (
                self.account['log'].get('Status', last_check)
                == accountStatus.LOCKED
            ):
                return 'Your account has been locked'
            elif (
                self.account['log'].get('Status', last_check)
                == accountStatus.UNUSUAL_ACTIVITY
            ):
                return 'Unusual activity detected'
            elif (
                self.account['log'].get('Status', last_check)
                == accountStatus.SEARCH_WORDS_ERROR
            ):
                return "Couldn't get search words"
            elif (
                self.account['log'].get('Status', last_check)
                == accountStatus.ERROR
            ):
                return 'Unknown error'
            elif (
                self.account['log'].get('Status', last_check)
                == accountStatus.PC_LOGIN_FAILED
            ):
                return "Couldn't login to PC"
            elif (
                self.account['log'].get('Status', last_check)
                == accountStatus.MOBILE_LOGIN_FAILED
            ):
                return "Couldn't login to mobile"
            elif (
                self.account['log'].get('Status', last_check)
                == accountStatus.PROXY_DEAD
            ):
                return 'Proxy did not work'
            else:
                return f"{self.account['log']['Last check']} | {self.account['log'].get('Status', accountStatus.NOT_FARMED)}"
        else:
            return f"{self.account['log']['Last check']}"

    def set_tint_on_card(self):
        if self.is_farmed():
            self.card.surface_tint_color = ft.colors.GREEN_500
            self.card.shadow_color = ft.colors.GREEN
        elif self.account['log']['Status'] in accountStatus.error_list():
            self.card.surface_tint_color = ft.colors.AMBER_500
            self.card.shadow_color = ft.colors.AMBER
        elif self.account['log']['Status'] == accountStatus.SUSPENDED:
            self.card.surface_tint_color = ft.colors.RED_500
            self.card.shadow_color = ft.colors.RED
        else:
            return


class Accounts(ft.UserControl):
    def __init__(self, parent, page: ft.Page):
        from .app_layout import UserInterface

        super().__init__()
        self.page = page
        self.parent: UserInterface = parent
        self.color_scheme = parent.color_scheme
        self.accounts_cards = None

        self.ui()
        self.page.update()

    def ui(self):
        self.title = ft.Row(
            controls=[
                ft.Text(
                    value='Accounts',
                    font_family='SF thin',
                    size=24,
                    weight=ft.FontWeight.BOLD,
                    text_align='center',
                    expand=True,
                ),
            ]
        )
        self.accounts_container = AccountsContainer(self.page, self)
        self.no_accounts_description = ft.Row(
            [
                ft.Text(
                    'No accounts file added yet, open an accounts file from Home',
                    expand=True,
                    text_align='center',
                    font_family='SF regular',
                    size=18,
                )
            ],
            visible=False,
        )
        self.filter_by = ft.Dropdown(
            border_color=self.color_scheme,
            dense=True,
            expand=6,
            value='All',
            on_change=lambda e: self.accounts_container._filter(
                e.control.value
            ),
            options=[
                ft.dropdown.Option('All'),
                ft.dropdown.Option('Farmed'),
                ft.dropdown.Option('Locked'),
                ft.dropdown.Option('Suspended'),
                ft.dropdown.Option('Accounts with error'),
                ft.dropdown.Option('0 < Points <5000'),
                ft.dropdown.Option('5000 < Points < 10000'),
                ft.dropdown.Option('10000 < Points < 15000'),
                ft.dropdown.Option('15000 < Points'),
            ],
        )
        self.search_field = ft.TextField(
            label='Search',
            border_color=self.color_scheme,
            dense=True,
            expand=4,
            on_submit=lambda e: self.accounts_container.search(
                e.control.value
            ),
        )
        self.search_button = ft.IconButton(
            icon=ft.icons.SEARCH,
            icon_color=self.color_scheme,
            on_click=lambda _: self.accounts_container.search(
                self.search_field.value
            ),
        )
        self.clear_button = ft.IconButton(
            icon=ft.icons.CLOSE,
            icon_color=self.color_scheme,
            on_click=self.accounts_container.clear_search,
        )
        self.buttons = ft.FilledTonalButton(
            expand=2,
            height=50,
            content=ft.Row(
                controls=[self.search_button, self.clear_button],
                alignment='center',
            ),
        )
        self.reset_logs_button = ft.TextButton(
            text='Reset all logs',
            icon=ft.icons.RESTART_ALT,
            icon_color=self.color_scheme,
            on_click=self.reset_all_logs,
        )
        self.finish_all_logs_button = ft.TextButton(
            text='Finish all logs',
            icon=ft.icons.CHECK,
            icon_color=self.color_scheme,
            on_click=self.set_all_accounts_to_finished,
        )
        self.control_bar = ft.Card(
            visible=False,
            content=ft.Container(
                margin=ft.margin.all(15),
                content=ft.Column(
                    spacing=20,
                    controls=[
                        ft.ListTile(
                            leading=ft.Icon(ft.icons.FILTER_LIST),
                            title=ft.Text('Control bar of accounts'),
                            subtitle=ft.Text(
                                'Filter accounts by status and points or search for a specific account'
                            ),
                            trailing=ft.IconButton(
                                ft.icons.ARROW_UPWARD_ROUNDED,
                                on_click=self.minimize_control_bar,
                            ),
                        ),
                        ft.Row(
                            controls=[
                                self.filter_by,
                                ft.VerticalDivider(width=10),
                                self.search_field,
                                self.buttons,
                            ]
                        ),
                        ft.Row(
                            [
                                self.reset_logs_button,
                                self.finish_all_logs_button,
                            ],
                            alignment='end',
                        ),
                    ],
                ),
            ),
        )
        # add button
        self.page.floating_action_button = ft.FloatingActionButton(
            text='Add account',
            icon=ft.icons.ADD,
            bgcolor=self.color_scheme,
            on_click=self.open_add_account_dialog,
            visible=True if self.page.route == '/accounts' else False,
        )

        # add account page fields
        self.email_field = ft.TextField(
            label='Email',
            border_color=self.color_scheme,
            text_size=12,
            multiline=False,
            dense=True,
            error_style=ft.TextStyle(color='red'),
            on_change=lambda _: self.check_field(self.email_field),
        )
        self.password_field = ft.TextField(
            label='Password',
            password=True,
            can_reveal_password=True,
            border_color=self.color_scheme,
            text_size=12,
            multiline=False,
            dense=True,
            error_style=ft.TextStyle(color='red'),
            on_change=lambda _: self.check_field(self.password_field),
        )
        self.proxy_field = ft.TextField(
            label='Proxy address (Optional)',
            tooltip='The proxy you entered here will be used when farming the account.',
            border_color=self.color_scheme,
            text_size=12,
            disabled=True,
            multiline=False,
            dense=True,
            error_style=ft.TextStyle(color='red'),
            on_change=lambda _: self.check_field(self.proxy_field),
        )
        self.proxy_check_box = ft.Checkbox(
            label='Use proxy',
            scale=0.95,
            fill_color=self.color_scheme,
            on_change=lambda _: self.field_status_update(
                self.proxy_check_box.value, self.proxy_field
            ),
        )
        self.mobile_user_agent_field = ft.TextField(
            label='Mobile user agent (Optional)',
            tooltip='This user agent will be used when farming the account for mobile device.',
            border_color=self.color_scheme,
            text_size=12,
            disabled=True,
            dense=True,
            multiline=False,
            error_style=ft.TextStyle(color='red'),
            on_change=lambda _: self.check_field(self.mobile_user_agent_field),
        )
        self.mobile_user_agent_check_box = ft.Checkbox(
            label='Use mobile user agent',
            scale=0.95,
            fill_color=self.color_scheme,
            on_change=lambda _: self.field_status_update(
                self.mobile_user_agent_check_box.value,
                self.mobile_user_agent_field,
            ),
        )

        # add/edit account dialog
        self.dialog_title = ft.Text('Add account', text_align='center')
        self.save_button = ft.ElevatedButton('Save', on_click=self.add_account)
        self.add_account_dialog = ft.AlertDialog(
            title=self.dialog_title,
            modal=True,
            content_padding=15,
            content=ft.Container(
                width=400,
                content=ft.Column(
                    height=350,
                    controls=[
                        ft.Row(
                            wrap=True,
                            controls=[
                                self.email_field,
                                self.password_field,
                                ft.Divider(),
                                self.proxy_field,
                                self.proxy_check_box,
                                self.mobile_user_agent_field,
                                self.mobile_user_agent_check_box,
                            ],
                        )
                    ],
                ),
            ),
            actions=[
                self.save_button,
                ft.ElevatedButton(
                    'Cancel', on_click=self.close_account_dialog
                ),
            ],
            actions_alignment='end',
            on_dismiss=self.reset_fields_to_default,
        )

        self.confirm_delete_button = ft.ElevatedButton(text='Yes')
        self.delete_dialog = ft.AlertDialog(
            title=ft.Text('Confirm delete'),
            modal=True,
            content=ft.Text('Do you really want to delete the account?'),
            actions=[
                self.confirm_delete_button,
                ft.ElevatedButton(
                    text='No', on_click=self.close_delete_dialog
                ),
            ],
            actions_alignment='end',
        )
        self.browser_running_dialog = ft.AlertDialog(
            title=ft.Text('Browser running'),
            modal=True,
            content=ft.Text(
                'Press ok when you done browsing to close browser.'
            ),
            actions=[
                ft.ElevatedButton(
                    text='Ok', on_click=self.close_browser_dialog
                )
            ],
            on_dismiss=self.close_browser_dialog,
            actions_alignment='center',
        )

        self.accounts_page_content = ft.Column(
            scroll='auto',
            alignment=ft.MainAxisAlignment.START,
            horizontal_alignment='stretch',
            expand=True,
            controls=[
                ft.Container(
                    margin=ft.margin.all(25),
                    alignment=ft.alignment.top_center,
                    content=ft.Column(
                        alignment=ft.MainAxisAlignment.START,
                        controls=[
                            self.title,
                            ft.Divider(),
                            self.control_bar,
                            self.no_accounts_description,
                            self.accounts_container,
                        ],
                    ),
                )
            ],
        )

    def build(self):
        return self.accounts_page_content

    def toggle_theme_mode(self, color_scheme):
        self.color_scheme = color_scheme
        self.filter_by.border_color = color_scheme
        self.search_field.border_color = color_scheme
        self.search_button.icon_color = color_scheme
        self.clear_button.icon_color = color_scheme
        self.reset_logs_button.icon_color = color_scheme
        self.finish_all_logs_button.icon_color = color_scheme
        self.email_field.border_color = color_scheme
        self.password_field.border_color = color_scheme
        self.proxy_field.border_color = color_scheme
        self.proxy_check_box.fill_color = color_scheme
        self.mobile_user_agent_field.border_color = color_scheme
        self.mobile_user_agent_check_box.fill_color = color_scheme
        self.page.floating_action_button.bgcolor = color_scheme

    def sync_accounts(self):
        if self.page.session.contains_key('MRFarmer.accounts'):
            self.accounts_container.refresh()
            self.accounts_container.visible = True
            self.control_bar.visible = True
            self.no_accounts_description.visible = False
        else:
            self.remove_accounts()
        self.page.update()

    def remove_accounts(self):
        self.no_accounts_description.visible = True
        self.accounts_container.visible = False
        self.control_bar.visible = False
        self.page.update()

    def open_add_account_dialog(self, e):
        self.dialog_title.value = 'Add account'
        if not self.page.session.contains_key('MRFarmer.accounts'):
            self.parent.display_error(
                'Accounts file not does not exist!',
                'Open accounts file from Home first then try to add an account.',
            )
            return
        self.page.dialog = self.add_account_dialog
        self.add_account_dialog.open = True
        self.page.update()

    def close_account_dialog(self, e):
        self.add_account_dialog.open = False
        self.reset_fields_to_default(e)
        self.page.update()

    def field_status_update(self, value: bool, control: ft.TextField):
        """Used to change disable attribute of proxy and mobile user agent TextField"""
        control.disabled = not value
        if not value and control.error_text:
            control.error_text = None
        self.page.update()

    def are_fields_valid(self):
        is_valid = True
        error_count = 0
        if not self.email_field.value:
            self.email_field.error_text = 'Email is required'
            error_count += 1
            is_valid = False
        if not self.password_field.value:
            self.password_field.error_text = 'Password is required'
            error_count += 1
            is_valid = False
        if self.proxy_check_box.value and not self.proxy_field.value:
            self.proxy_field.error_text = 'Proxy is required'
            error_count += 1
            is_valid = False
        if (
            self.mobile_user_agent_check_box.value
            and not self.mobile_user_agent_field.value
        ):
            self.mobile_user_agent_field.error_text = (
                'Mobile user agent is required'
            )
            error_count += 1
            is_valid = False
        dialog_height = 350 + (error_count * 25)
        self.add_account_dialog.content.content.height = dialog_height
        if not is_valid:
            self.page.update()
        return is_valid

    def check_field(self, control: ft.TextField):
        """Check fields in add/edit account for error and remove the error text and reduce height of dialog"""
        if control.value and control.error_text:
            control.error_text = None
            self.add_account_dialog.content.content.height -= 25
            self.page.update()

    def add_account(self, e):
        if self.are_fields_valid():
            accounts: list = self.page.session.get('MRFarmer.accounts')
            account = {
                'username': self.email_field.value,
                'password': self.password_field.value,
                'log': {
                    'Last check': str(date.today()),
                    'Status': 'Not farmed',
                    "Today's points": 0,
                    'Points': 0,
                    'Daily': False,
                    'Punch cards': False,
                    'More promotions': False,
                    'MSN shopping game': False,
                    'PC searches': False,
                    'Mobile searches': False,
                },
            }
            if self.proxy_check_box.value:
                account['proxy'] = self.proxy_field.value
            if self.mobile_user_agent_check_box.value:
                account[
                    'mobile_user_agent'
                ] = self.mobile_user_agent_field.value
            accounts.append(account)
            self.page.session.set('MRFarmer.accounts', accounts)
            self.sync_accounts()
            self.parent.update_accounts_file()
            self.close_account_dialog(e)

    def reset_fields_to_default(self, e):
        fields = [
            self.email_field,
            self.password_field,
            self.proxy_field,
            self.mobile_user_agent_field,
        ]
        checkboxes = [self.proxy_check_box, self.mobile_user_agent_check_box]
        self.proxy_field.disabled = True
        self.mobile_user_agent_field.disabled = True
        for field in fields:
            field.value = None
            field.error_text = None
        for checkbox in checkboxes:
            checkbox.value = False
        self.add_account_dialog.content.content.height = 350
        self.dialog_title.value = 'Add account'
        self.save_button.on_click = self.add_account
        self.page.update()

    def open_delete_dialog(self, account: str):
        if self.parent.is_farmer_running:
            self.parent.display_error(
                "Can't delete account",
                'Stop farmer first then try to delete account',
            )
            return
        self.page.dialog = self.delete_dialog
        self.confirm_delete_button.on_click = lambda _: self.delete_account(
            account
        )
        self.delete_dialog.open = True
        self.page.update()

    def close_delete_dialog(self, e):
        self.delete_dialog.open = False
        self.page.update()

    def delete_account(self, account: str):
        self.close_delete_dialog(None)
        accounts: list = self.page.session.get('MRFarmer.accounts')
        if len(accounts) == 1:
            self.parent.display_error(
                "Can't delete account", 'You must have at least one account'
            )
            return
        for i, acc in enumerate(accounts):
            if acc['username'] == account:
                accounts.pop(i)
                break
        self.page.session.set('MRFarmer.accounts', accounts)
        self.sync_accounts()
        self.parent.update_accounts_file()

    def set_value_to_fields(self, e, account: dict):
        """Set selected account's values to fields to edit and open edit dialog"""
        if self.parent.is_farmer_running:
            self.parent.display_error(
                "Can't edit account",
                'Stop farmer first then try to edit account',
            )
            return
        self.dialog_title.value = 'Edit Account'
        for i, acc in enumerate(self.page.session.get('MRFarmer.accounts')):
            if acc['username'] == account['username']:
                self.save_button.on_click = lambda _: self.save_edited_account(
                    i
                )
                break
        self.email_field.value = account['username']
        self.password_field.value = account['password']
        if 'proxy' in account.keys():
            self.proxy_field.value = account['proxy']
            self.proxy_check_box.value = True
            self.proxy_field.disabled = False
        if 'mobile_user_agent' in account.keys():
            self.mobile_user_agent_field.value = account['mobile_user_agent']
            self.mobile_user_agent_check_box.value = True
            self.mobile_user_agent_field.disabled = False
        self.page.dialog = self.add_account_dialog
        self.add_account_dialog.open = True
        self.page.update()

    def save_edited_account(self, index: int):
        if self.are_fields_valid():
            accounts = self.page.session.get('MRFarmer.accounts')
            account = accounts[index]
            account['username'] = self.email_field.value
            account['password'] = self.password_field.value
            if self.proxy_check_box.value:
                account['proxy'] = self.proxy_field.value
            else:
                account.pop('proxy', None)
            if self.mobile_user_agent_check_box.value:
                account[
                    'mobile_user_agent'
                ] = self.mobile_user_agent_field.value
            else:
                account.pop('mobile_user_agent', None)
            accounts[index] = account
            self.page.session.set('MRFarmer.accounts', accounts)
            self.sync_accounts()
            self.parent.update_accounts_file()
            self.close_account_dialog(None)

    def clear_account_log(self, account: str):
        if self.parent.is_farmer_running:
            self.parent.display_error(
                'Farmer is running',
                "You can't reset log when farmer is running",
            )
            return
        accounts = self.page.session.get('MRFarmer.accounts')
        for acc in accounts:
            if acc['username'] == account:
                acc['log']['Last check'] = str(date.today())
                acc['log']['Status'] = 'Not farmed'
                if not isinstance(acc['log']["Today's points"], int):
                    acc['log']["Today's points"] = 0
                if not isinstance(acc['log']['Points'], int):
                    acc['log']['Points'] = 0
                acc['log'].pop('Daily', None)
                acc['log'].pop('Punch cards', None)
                acc['log'].pop('More promotions', None)
                acc['log'].pop('MSN shopping game', None)
                acc['log'].pop('PC searches', None)
                acc['log'].pop('Mobile searches', None)
                break
        self.page.session.set('MRFarmer.accounts', accounts)
        self.sync_accounts()
        self.parent.update_accounts_file()

    def reset_all_logs(self, e: ft.ControlEvent):
        if self.parent.is_farmer_running:
            self.parent.display_error(
                'Farmer is running',
                "You can't reset logs when farmer is running",
            )
            return
        accounts = self.page.session.get('MRFarmer.accounts')
        for account in accounts:
            account['log']['Last check'] = str(date.today())
            account['log']['Status'] = 'Not farmed'
            if not isinstance(account['log']["Today's points"], int):
                account['log']["Today's points"] = 0
            if not isinstance(account['log']['Points'], int):
                account['log']['Points'] = 0
            account['log'].pop('Daily', None)
            account['log'].pop('Punch cards', None)
            account['log'].pop('More promotions', None)
            account['log'].pop('MSN shopping game', None)
            account['log'].pop('PC searches', None)
            account['log'].pop('Mobile searches', None)
        self.page.session.set('MRFarmer.accounts', accounts)
        self.accounts_container.refresh()
        self.parent.update_accounts_file()

    def set_account_to_finished(self, account: str):
        if self.parent.is_farmer_running:
            self.parent.display_error(
                'Farmer is running',
                "You can't set account to finished when farmer is running",
            )
            return
        accounts = self.page.session.get('MRFarmer.accounts')
        for acc in accounts:
            if acc['username'] == account:
                acc['log']['Last check'] = str(date.today())
                acc['log']['Status'] = 'Farmed'
                acc['log'].pop('Daily', None)
                acc['log'].pop('Punch cards', None)
                acc['log'].pop('More promotions', None)
                acc['log'].pop('MSN shopping game', None)
                acc['log'].pop('PC searches', None)
                acc['log'].pop('Mobile searches', None)
                break
        self.page.session.set('MRFarmer.accounts', accounts)
        self.sync_accounts()
        self.parent.update_accounts_file()

    def set_all_accounts_to_finished(self, e: ft.ControlEvent):
        if self.parent.is_farmer_running:
            self.parent.display_error(
                'Farmer is running',
                "You can't set account to finished when farmer is running",
            )
            return
        accounts = self.page.session.get('MRFarmer.accounts')
        for account in accounts:
            account['log']['Last check'] = str(date.today())
            account['log']['Status'] = 'Farmed'
            account['log'].pop('Daily', None)
            account['log'].pop('Punch cards', None)
            account['log'].pop('More promotions', None)
            account['log'].pop('MSN shopping game', None)
            account['log'].pop('PC searches', None)
            account['log'].pop('Mobile searches', None)
        self.page.session.set('MRFarmer.accounts', accounts)
        self.sync_accounts()
        self.parent.update_accounts_file()

    def open_session_browser(self, account: dict):
        """Open session browser and dialog for account"""
        if self.parent.is_farmer_running:
            self.parent.display_error(
                "Can't open browser",
                'Stop farmer first then try to open browser',
            )
            return
        self.is_browser_running = True
        self.browser_running_dialog.content = ft.Text(
            f"Press ok when you done browsing to close browser.\n\nAccount name: {account.get('username')}"
        )
        self.page.dialog = self.browser_running_dialog
        self.browser_running_dialog.open = True
        self.page.update()
        try:
            Farmer.account_browser(self.page, account, self)
        except (SessionNotCreatedException, WebDriverException):
            self.close_browser_dialog(None)
            time.sleep(1)
            self.is_browser_running = False
            self.parent.display_error(
                'Webdriver error',
                'Webdriver not found or outdated. Please update your webdriver.',
            )
            return

    def close_browser_dialog(self, e):
        self.is_browser_running = False
        self.browser_running_dialog.open = False
        self.page.update()

    def is_browser_running_status(self):
        """This function constantly checkes by account browser in Farmer to know when to close browser"""
        return self.is_browser_running

    def minimize_control_bar(self, e: ft.ControlEvent):
        controls = self.control_bar.content.content.controls
        if e.control.icon == 'arrow_upward_rounded':
            controls[1].visible = False
            controls[2].visible = False
            e.control.icon = ft.icons.ARROW_DOWNWARD_ROUNDED
        else:
            controls[1].visible = True
            controls[2].visible = True
            e.control.icon = ft.icons.ARROW_UPWARD_ROUNDED
        self.page.update()
