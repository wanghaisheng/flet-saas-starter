import json
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import flet as ft
import requests
from flet import theme

from src.core import MOBILE_USER_AGENT, PC_USER_AGENT
from src.core.other_functions import resource_path
from src.utils import constants

from .about import __VERSION__, About
from .accounts import Accounts
from .discord import Discord
from .home import Home
from .responsive_menu_layout import ResponsiveMenuLayout
from .settings import Settings
from .telegram import Telegram

LIGHT_SEED_COLOR = ft.colors.TEAL
DARK_SEED_COLOR = ft.colors.INDIGO


class UserInterface(ft.View):
    def __init__(self, page: ft.Page):
        super().__init__()
        self.page = page
        self.page.title = 'Microsoft Rewards Farmer'
        self.page.fonts = {
            'SF thin': 'fonts/SFUIDisplay-Thin.otf',
            'SF regular': 'fonts/SF-Pro-Display-Regular.otf',
            'SF light': 'fonts/SFUIText-Light.otf',
        }

        self.horizontal_alignment = ft.CrossAxisAlignment.CENTER
        self.page.window_prevent_close = True
        self.page.on_window_event = self.window_event
        if not self.page.client_storage.get('MRFarmer.has_run_before'):
            self.first_time_setup()
        self.page.theme_mode = self.page.client_storage.get(
            'MRFarmer.theme_mode'
        )
        self.light_theme_color = self.get_light_theme_color()
        self.dark_theme_color = self.get_dark_theme_color()
        self.color_scheme = self.get_color_scheme()
        self.page.theme = theme.Theme(color_scheme_seed=self.light_theme_color)
        self.page.dark_theme = theme.Theme(
            color_scheme_seed=self.dark_theme_color
        )
        self.page.window_height = 820
        self.page.window_width = 1280
        self.page.window_min_height = 795
        self.page.window_min_width = 765
        self.page.on_resize = self.on_page_resize
        self.page.window_center()
        self.page.on_route_change = self.on_route_change
        self.page.on_error = self.save_app_error
        self.is_farmer_running: bool = False
        self.is_checking_update: bool = False

        self.ui()
        self.page.update()
        self.auto_start_if_needed()
        self.check_for_update(None, True)

    def ui(self):
        menu_button = ft.IconButton(ft.icons.MENU)

        self.toggle_theme_button = ft.IconButton(
            ft.icons.MODE_NIGHT
            if self.page.theme_mode == 'light'
            else ft.icons.WB_SUNNY_ROUNDED,
            on_click=self.toggle_theme_mode,
        )

        self.update_progress_ring = ft.ProgressRing(
            scale=0.7, color=self.color_scheme, visible=False
        )
        self.update_icon = ft.Icon(ft.icons.UPDATE)
        self.check_update_button = ft.PopupMenuItem(
            content=ft.Row(
                controls=[
                    self.update_progress_ring,
                    self.update_icon,
                    ft.Text('Check for update'),
                ]
            ),
            on_click=self.check_for_update,
        )
        self.logout_button = ft.PopupMenuItem(
            content=ft.Row(
                controls=[ft.Icon(ft.icons.LOGOUT), ft.Text('Logout')]
            )
        )

        self.update_dialog = ft.AlertDialog(
            actions_alignment='center', modal=True, actions=[]
        )

        self.appbar = ft.AppBar(
            title=ft.Text('TikToka-Studio', font_family='SF regular'),
            leading=menu_button,
            leading_width=40,
            bgcolor=ft.colors.SURFACE_VARIANT,
            actions=[
                self.toggle_theme_button,
                ft.PopupMenuButton(
                    items=[
                        self.check_update_button,
                        ft.PopupMenuItem(),
                        ft.PopupMenuItem(
                            icon=ft.icons.RESTART_ALT,
                            text='Reset all settings',
                            on_click=self.reset_all_settings,
                        ),
                        ft.PopupMenuItem(),
                        self.logout_button,
                    ]
                ),
            ],
        )

        # Exit dialog confirmation
        self.exit_dialog = ft.AlertDialog(
            modal=False,
            title=ft.Text('Exit confirmation'),
            content=ft.Text('Do you really want to exit?'),
            actions=[
                ft.ElevatedButton(
                    'Yes', on_click=lambda _: self.page.window_destroy()
                ),
                ft.OutlinedButton('No', on_click=self.no_click),
            ],
            actions_alignment='end',
        )

        self.error_dialog = ft.AlertDialog(
            actions=[
                ft.ElevatedButton(
                    text='Ok',
                    on_click=lambda e: self.close_error(e, self.error_dialog),
                )
            ],
            actions_alignment='center',
        )

        self.snack_bar_message = ft.Text()
        self.page.snack_bar = ft.SnackBar(
            content=self.snack_bar_message, bgcolor=self.color_scheme
        )

        self.home_page = Home(self, self.page)
        self.settings_page = Settings(self, self.page)
        self.telegram_page = Telegram(self, self.page)
        self.discord_page = Discord(self, self.page)
        self.accounts_page = Accounts(self, self.page)
        self.about_page = About(self, self.page)

        pages = [
            (
                dict(
                    icon=ft.icons.HOME,
                    selected_icon=ft.icons.HOME,
                    label='Farmer',
                ),
                self.home_page.build(),
            ),
            (
                dict(
                    icon=ft.icons.PEOPLE_ALT,
                    selected_icon=ft.icons.PEOPLE_ALT,
                    label='Accounts',
                ),
                self.accounts_page.build(),
            ),
            (
                dict(
                    icon=ft.icons.TELEGRAM,
                    selected_icon=ft.icons.TELEGRAM,
                    label='Telegram',
                ),
                self.telegram_page.build(),
            ),
            (
                dict(
                    icon=ft.icons.DISCORD,
                    selected_icon=ft.icons.DISCORD,
                    label='Discord',
                ),
                self.discord_page.build(),
            ),
            (
                dict(
                    icon=ft.icons.SETTINGS,
                    selected_icon=ft.icons.SETTINGS,
                    label='Settings',
                ),
                self.settings_page.build(),
            ),
            (
                dict(
                    icon=ft.icons.INFO_ROUNDED,
                    selected_icon=ft.icons.INFO_ROUNDED,
                    label='About',
                ),
                self.about_page.build(),
            ),
        ]

        self.menu_layout = ResponsiveMenuLayout(
            self.page, pages, landscape_minimize_to_icons=True
        )
        menu_button.on_click = lambda e: self.menu_layout.toggle_navigation()
        # self.page.add(self.menu_layout)
        self.controls.append(self.menu_layout)
        self.page.update()

    def window_event(self, e):
        if e.data == 'close':
            self.page.dialog = self.exit_dialog
            self.exit_dialog.open = True
            self.page.update()

    def no_click(self, e):
        self.exit_dialog.open = False
        self.page.update()

    def toggle_theme_mode(self, e):
        self.page.theme_mode = (
            'dark' if self.page.theme_mode == 'light' else 'light'
        )
        self.page.client_storage.set(
            'MRFarmer.theme_mode', self.page.theme_mode
        )
        self.toggle_theme_button.icon = (
            ft.icons.MODE_NIGHT
            if self.page.theme_mode == 'light'
            else ft.icons.WB_SUNNY_ROUNDED
        )
        self.change_color_scheme()

    def change_color_scheme(self):
        self.color_scheme = self.get_color_scheme()
        self.page.snack_bar.bgcolor = self.color_scheme
        self.home_page.toggle_theme_mode(self.color_scheme)
        self.settings_page.toggle_theme_mode(self.color_scheme)
        self.telegram_page.toggle_theme_mode(self.color_scheme)
        self.discord_page.toggle_theme_mode(self.color_scheme)
        self.accounts_page.toggle_theme_mode(self.color_scheme)
        self.page.update()

    def first_time_setup(self):
        """If it's the first time that app being used, it sets the default values to client storage"""
        directory_path = Path.cwd()
        accounts_path = str(Path(f'{directory_path}\\accounts.json').resolve())
        self.page.client_storage.set('MRFarmer.has_run_before', True)
        self.page.client_storage.set('MRFarmer.theme_mode', 'dark')
        # home
        self.page.client_storage.set('MRFarmer.accounts_path', accounts_path)
        self.page.client_storage.set('MRFarmer.timer', '00:00')
        self.page.client_storage.set('MRFarmer.timer_switch', False)
        # settings
        ## user agent
        self.page.client_storage.set('MRFarmer.pc_user_agent', PC_USER_AGENT)
        self.page.client_storage.set(
            'MRFarmer.mobile_user_agent', MOBILE_USER_AGENT
        )
        ## global settings
        self.page.client_storage.set('MRFarmer.headless', False)
        self.page.client_storage.set('MRFarmer.speed', 'Normal')
        self.page.client_storage.set('MRFarmer.session', False)
        self.page.client_storage.set('MRFarmer.save_errors', False)
        self.page.client_storage.set('MRFarmer.shutdown', False)
        self.page.client_storage.set('MRFarmer.edge_webdriver', False)
        self.page.client_storage.set('MRFarmer.use_proxy', False)
        self.page.client_storage.set('MRFarmer.auto_start', False)
        self.page.client_storage.set('MRFarmer.skip_on_proxy_failure', False)
        ## farmer settings
        self.page.client_storage.set('MRFarmer.daily_quests', True)
        self.page.client_storage.set('MRFarmer.punch_cards', True)
        self.page.client_storage.set('MRFarmer.more_activities', True)
        self.page.client_storage.set('MRFarmer.pc_search', True)
        self.page.client_storage.set('MRFarmer.mobile_search', True)
        self.page.client_storage.set('MRFarmer.msn_shopping_game', False)
        ## theme settings
        self.page.client_storage.set(
            'MRFarmer.light_theme_color', LIGHT_SEED_COLOR
        )
        self.page.client_storage.set(
            'MRFarmer.light_widgets_color', LIGHT_SEED_COLOR
        )
        self.page.client_storage.set(
            'MRFarmer.dark_theme_color', DARK_SEED_COLOR
        )
        self.page.client_storage.set(
            'MRFarmer.dark_widgets_color', ft.colors.INDIGO_300
        )
        # telegram
        self.page.client_storage.set('MRFarmer.telegram_token', '')
        self.page.client_storage.set('MRFarmer.telegram_chat_id', '')
        self.page.client_storage.set('MRFarmer.send_to_telegram', False)
        self.page.client_storage.set('MRFarmer.telegram_proxy_switch', False)
        # discord
        self.page.client_storage.set('MRFarmer.discord_webhook_url', '')
        self.page.client_storage.set('MRFarmer.send_to_discord', False)

    def get_light_theme_color(self):
        if not self.page.client_storage.contains_key(
            'MRFarmer.light_theme_color'
        ):
            self.page.client_storage.set(
                'MRFarmer.light_theme_color', LIGHT_SEED_COLOR
            )
            return LIGHT_SEED_COLOR
        else:
            return self.page.client_storage.get('MRFarmer.light_theme_color')

    def get_dark_theme_color(self):
        if not self.page.client_storage.contains_key(
            'MRFarmer.dark_theme_color'
        ):
            self.page.client_storage.set(
                'MRFarmer.light_theme_color', DARK_SEED_COLOR
            )
            return DARK_SEED_COLOR
        else:
            return self.page.client_storage.get('MRFarmer.dark_theme_color')

    def get_color_scheme(self):
        if self.page.theme_mode == 'light':
            if not self.page.client_storage.contains_key(
                'MRFarmer.light_widgets_color'
            ):
                self.page.client_storage.set(
                    'MRFarmer.light_widgets_color', LIGHT_SEED_COLOR
                )
            return self.page.client_storage.get('MRFarmer.light_widgets_color')
        elif self.page.theme_mode == 'dark':
            if not self.page.client_storage.contains_key(
                'MRFarmer.dark_widgets_color'
            ):
                self.page.client_storage.set(
                    'MRFarmer.dark_widgets_color', ft.colors.INDIGO_300
                )
            return self.page.client_storage.get('MRFarmer.dark_widgets_color')

    def on_route_change(self, e):
        if e.data == '/accounts':
            self.page.floating_action_button.visible = True
        else:
            self.page.floating_action_button.visible = False
        self.page.update()

    def display_error(self, title: str, description: str):
        self.error_dialog.title = ft.Text(title)
        self.error_dialog.content = ft.Text(description)
        self.page.dialog = self.error_dialog
        self.error_dialog.open = True
        self.page.update()

    def open_snack_bar(self, message: str):
        self.snack_bar_message.value = message
        self.page.snack_bar.open = True
        self.page.update()

    def close_error(self, e, dialog: ft.AlertDialog):
        dialog.open = False
        self.page.update()

    def update_accounts_file(self):
        with open(
            resource_path(
                self.page.client_storage.get('MRFarmer.accounts_path')
            ),
            'w',
        ) as file:
            file.write(
                json.dumps(
                    self.page.session.get('MRFarmer.accounts'), indent=4
                )
            )

    def save_app_error(self, e):
        if (
            e.data
            == "type 'bool' is not a subtype of type 'List<dynamic>?' in type cast"
        ):
            return
        if not self.page.client_storage.get('MRFarmer.save_errors'):
            with open(resource_path('errors.txt', True), 'a') as f:
                f.write(
                    f'\n-------------------{datetime.now()}-------------------\r\n'
                )
                f.write('APP_ERROR:\n')
                f.write(f'{e.data}\n')

    def get_farming_status(self):
        """checks by farmer to know stop or continue farming"""
        return self.is_farmer_running

    def auto_start_if_needed(self):
        """Start to Farm if auto start is enabled at startup"""
        if self.page.session.contains_key(
            'MRFarmer.accounts'
        ) and self.page.client_storage.get('MRFarmer.auto_start'):
            self.home_page.start(None)
        elif not self.page.session.contains_key(
            'MRFarmer.accounts'
        ) and self.page.client_storage.get('MRFarmer.auto_start'):
            self.display_error(
                'Auto start failed',
                'Could not start auto farming because there is no accounts',
            )
            self.page.update()

    def on_page_resize(self, e: ft.ControlEvent):
        try:
            self.menu_layout.handle_resize(e)
            self.accounts_page.accounts_container.refresh()
            width = float(e.data.split(',')[0])
            if width < 1140:
                self.settings_page.msn_shopping_game_switch.label = 'MSN'
                self.page.update()
            elif (
                width >= 1140
                and self.settings_page.msn_shopping_game_switch.label == 'MSN'
            ):
                self.settings_page.msn_shopping_game_switch.label = (
                    'MSN shopping Game'
                )
                self.page.update()
        except AttributeError:
            pass

    def check_for_update(self, e: ft.ControlEvent, on_start: bool = False):
        def download(tag_name: str):
            download_btn.disabled = True
            close_btn.disabled = True
            self.update_dialog.content = ft.Column(
                [
                    ft.Text('Downloading...'),
                    ft.ProgressBar(width=300, color=self.color_scheme),
                ],
                height=50,
            )
            self.page.update()
            download_url = f'https://github.com/farshadz1997/Microsoft-Rewards-bot-GUI-V2/archive/refs/tags/{tag_name}.zip'
            try:
                response = requests.get(download_url)
                if response.status_code == 200:
                    with open(
                        resource_path(
                            f"Microsoft-Rewards-bot-GUI-V2_{release_info['name']}.zip",
                            True,
                        ),
                        'wb',
                    ) as f:
                        f.write(response.content)
                    self.update_dialog.content = ft.Column(
                        [
                            ft.Text('Download completed'),
                            ft.ProgressBar(
                                width=300, color='green', value=100
                            ),
                        ],
                        height=50,
                    )
                    download_btn.disabled = False
                    close_btn.disabled = False
                    self.page.update()
                else:
                    raise Exception
            except:
                self.update_dialog.content = ft.Column(
                    [
                        ft.Text('Download failed'),
                        ft.ProgressBar(width=300, color='red', value=100),
                    ],
                    height=50,
                )
                download_btn.disabled = False
                close_btn.disabled = False
                self.page.update()

        if self.is_checking_update:
            return
        self.is_checking_update = True
        self.check_update_button.disabled = True
        self.update_progress_ring.visible = True
        self.update_icon.visible = False
        self.page.update()
        headers = {'Accept': 'application/vnd.github.v3+json'}
        url = 'https://api.github.com/repos/farshadz1997/Microsoft-Rewards-bot-GUI-V2/releases/latest'
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                release_info = json.loads(response.text)
                latest_version = release_info['tag_name']
                self.page.dialog = self.update_dialog
                if float(latest_version) > __VERSION__:
                    self.update_dialog.actions.clear()
                    self.update_dialog.title = ft.Text(
                        'New version available!'
                    )
                    self.update_dialog.content = ft.Markdown(
                        release_info['body'],
                        on_tap_link=lambda e: webbrowser.open(e.data),
                    )
                    download_btn = ft.ElevatedButton(
                        text='Download',
                        on_click=lambda _: download(latest_version),
                    )
                    self.update_dialog.actions.append(download_btn)
                    close_btn = ft.ElevatedButton(
                        text='Close',
                        on_click=lambda e: self.close_error(
                            e, self.update_dialog
                        ),
                    )
                    self.update_dialog.actions.append(close_btn)
                    self.update_dialog.open = True
                    self.page.update()
                else:
                    if not on_start:
                        self.update_dialog.actions.clear()
                        self.update_dialog.title = ft.Text(
                            'No new version available'
                        )
                        self.update_dialog.content = ft.Text(
                            'You are using the latest version of the app'
                        )
                        self.update_dialog.actions.append(
                            ft.ElevatedButton(
                                text='Ok',
                                on_click=lambda e: self.close_error(
                                    e, self.update_dialog
                                ),
                            ),
                        )
                        self.page.dialog.open = True
                        self.page.update()
            else:
                if not on_start:
                    self.display_error(
                        'Update check failed', 'Could not check for update'
                    )
        except:
            if not on_start:
                self.display_error(
                    'Update check failed', 'Could not check for update'
                )
        finally:
            self.check_update_button.disabled = False
            self.update_progress_ring.visible = False
            self.update_icon.visible = True
            self.is_checking_update = False
            self.page.update()

    def reset_all_settings(self, e: ft.ControlEvent):
        if self.is_farmer_running:
            self.display_error(
                'Reset failed', 'Could not reset settings while farming'
            )
            return
        self.page.client_storage.clear()
        self.page.session.clear()
        self.first_time_setup()
        self.home_page.set_initial_values()
        self.telegram_page.set_initial_values()
        self.settings_page.set_initial_values()
        self.toggle_theme_mode(None)
        self.page.update()
