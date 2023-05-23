import flet as ft
from flet import theme


# python
from typing import Dict
from typing import List
from typing import Optional


from src.core.handler import Handler


from .home import Home
from .settings import Settings
from .telegram import Telegram
from .discord import Discord
from .accounts import Accounts
from .about import About, __VERSION__
from src.core import PC_USER_AGENT, MOBILE_USER_AGENT
from .responsive_menu_layout import ResponsiveMenuLayout
from pathlib import Path
import json
from datetime import datetime
import requests, webbrowser
from src.core.other_functions import resource_path

from src.utils import constants

LIGHT_SEED_COLOR = ft.colors.TEAL
DARK_SEED_COLOR = ft.colors.INDIGO


class IncompletedItem(ft.Row):
    def __init__(self, primary_key: int, description: str) -> None:
        super().__init__()
        self.primary_key = primary_key

        self.description = ft.Text()
        self.description.value = description
        self.description.text_align = ft.TextAlign.CENTER
        self.description.expand = True

        self.complete_button = ft.IconButton()
        self.complete_button.icon = ft.icons.CHECK
        self.complete_button.tooltip = 'Complete'
        self.complete_button.icon_color = ft.colors.GREEN

        self.delete_button = ft.IconButton()
        self.delete_button.icon = ft.icons.DELETE
        self.delete_button.tooltip = 'Delete'
        self.delete_button.icon_color = ft.colors.RED

        self.controls.append(self.description)
        self.controls.append(self.complete_button)
        self.controls.append(self.delete_button)


class CompletedItem(ft.Row):
    def __init__(self, primary_key: int, description: str) -> None:
        super().__init__()
        self.primary_key = primary_key

        self.description = ft.Text()
        self.description.value = description
        self.description.text_align = ft.TextAlign.CENTER
        self.description.expand = True

        self.incomplete_button = ft.IconButton()
        self.incomplete_button.icon = ft.icons.CANCEL
        self.incomplete_button.tooltip = 'Incomplete'
        self.incomplete_button.icon_color = ft.colors.AMBER

        self.delete_button = ft.IconButton()
        self.delete_button.icon = ft.icons.DELETE
        self.delete_button.tooltip = 'Delete'
        self.delete_button.icon_color = ft.colors.RED

        self.controls.append(self.description)
        self.controls.append(self.incomplete_button)
        self.controls.append(self.delete_button)


class WarningBanner(ft.Banner):
    def __init__(self, page: ft.Page, message: str) -> None:
        super().__init__()
        self.page = page
        self.bgcolor = ft.colors.RED

        self.message = ft.Text()
        self.message.value = message
        self.message.text_align = ft.TextAlign.CENTER
        self.message.color = ft.colors.WHITE
        self.message.expand = True

        self.leading = ft.Icon()
        self.leading.name = ft.icons.DANGEROUS
        self.leading.color = ft.colors.WHITE

        self.close_button = ft.IconButton()
        self.close_button.icon = ft.icons.CLOSE
        self.close_button.icon_color = ft.colors.WHITE
        self.close_button.on_click = lambda e: self.close()
        self.actions.append(self.close_button)

        self.content = ft.Row()
        self.content.controls.append(self.message)

    def close(self) -> None:
        self.page.banner.open = False
        self.page.update()


class SuccessSnackBar(ft.SnackBar):
    def __init__(self, message: str) -> None:
        super().__init__(content=ft.Row())
        self.bgcolor = ft.colors.GREEN

        self.message = ft.Text()
        self.message.value = message
        self.message.text_align = ft.TextAlign.CENTER
        self.message.color = ft.colors.WHITE
        self.message.size = 20
        self.message.expand = True

        self.content.controls.append(self.message)


class LoginView(ft.View):
    def __init__(self) -> None:
        super().__init__()
        self.horizontal_alignment = ft.CrossAxisAlignment.CENTER

        self.title = ft.Text()
        self.title.value = 'Login'
        self.title.style = ft.TextThemeStyle.DISPLAY_MEDIUM
        self.title.text_align = ft.TextAlign.CENTER
        self.title.expand = True

        self.username_field = ft.TextField()
        self.username_field.label = 'Username'
        self.username_field.expand = True

        self.password_field = ft.TextField()
        self.password_field.label = 'Password'
        self.password_field.password = True
        self.password_field.can_reveal_password = True
        self.password_field.expand = True

        self.login_button = ft.OutlinedButton()
        self.login_button.text = 'Sign In'
        self.login_button.icon = ft.icons.LOGIN
        self.login_button.expand = True

        self.register_button = ft.TextButton()
        self.register_button.text = "Don' Have An Account? Sign Up"
        self.register_button.icon = ft.icons.ARROW_FORWARD
        self.register_button.expand = True

        content = ft.Column()
        content.width = 400
        content.alignment = ft.MainAxisAlignment.CENTER
        content.controls.append(ft.Row([self.title]))
        content.controls.append(ft.Row([self.username_field]))
        content.controls.append(ft.Row([self.password_field]))
        content.controls.append(ft.Row([self.login_button]))
        content.controls.append(ft.Row([self.register_button]))

        container = ft.Container()
        container.content = content
        container.border = ft.border.all(1, ft.colors.TRANSPARENT)
        container.expand = True
        self.controls.append(container)

class ApplicationAppBar(ft.AppBar):
    def __init__(self) -> None:
        super().__init__()

        self.title = ft.Text()
        self.title.value = 'Tiktoka Studio'
        self.leading = self.title

        self.logout_button = ft.IconButton()
        self.logout_button.icon = ft.icons.LOGOUT
        self.logout_button.tooltip = 'Logout'
        self.actions.append(self.logout_button)
class RegisterView(LoginView):
    def __init__(self) -> None:
        super().__init__()
        self.title.value = 'Register'
        self.login_button, self.register_button = (
            self.register_button,
            self.login_button,
        )
        self.register_button.text = 'Sign Up'
        self.login_button.text = 'Already Have An Account? Sign in'
class TodolistView(ft.View):
    def __init__(self) -> None:
        super().__init__()
        self.horizontal_alignment = ft.CrossAxisAlignment.CENTER
        self.appbar = ApplicationAppBar()
                
        
        self.description_field = ft.TextField()
        self.description_field.label = 'What need to be done?'
        self.description_field.expand = True

        self.add_todo_button = ft.IconButton()
        self.add_todo_button.icon = ft.icons.ADD
        self.add_todo_button.tooltip = 'Add'

        self.incompleted_listview = ft.ListView()
        self.incompleted_listview.spacing = 20
        self.incompleted_listview.expand = True

        self.completed_listview = ft.ListView()
        self.completed_listview.spacing = 20
        self.completed_listview.expand = True

        self.incompleted_tab = ft.Tab()
        self.incompleted_tab.text = 'Incompleted'
        self.incompleted_tab.icon = ft.icons.CANCEL
        self.incompleted_tab.content = self.incompleted_listview
        self.incompleted_tab.content.expand = True

        self.completed_tab = ft.Tab()
        self.completed_tab.text = 'Completed'
        self.completed_tab.icon = ft.icons.CHECK
        self.completed_tab.content = self.completed_listview
        self.completed_tab.content.expand = True

        self.tabs_container = ft.Tabs()
        self.tabs_container.animation_duration = 500
        self.tabs_container.tabs.append(self.incompleted_tab)
        self.tabs_container.tabs.append(self.completed_tab)
        self.tabs_container.expand = True

        content = ft.Column()
        content.width = 600
        content.controls.append(
            ft.Row([self.description_field, self.add_todo_button])
        )
        content.controls.append(self.tabs_container)

        container = ft.Container()
        container.content = content
        container.border = ft.border.all(1, ft.colors.TRANSPARENT)
        container.expand = True
        self.controls.append(container)
        self.todo_page_content = content
    def build(self):
        return self.todo_page_content
class UserInterface:
    
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "Microsoft Rewards Farmer"
        page.fonts = {
            "SF thin": "fonts/SFUIDisplay-Thin.otf",
            "SF regular": "fonts/SF-Pro-Display-Regular.otf",
            "SF light": "fonts/SFUIText-Light.otf"
        }

        self.horizontal_alignment = ft.CrossAxisAlignment.CENTER

        self.appbar = ApplicationAppBar()

        self.page.window_prevent_close = True
        self.page.on_window_event = self.window_event
        if not self.page.client_storage.get("MRFarmer.has_run_before"):
            self.first_time_setup()
        self.page.theme_mode = self.page.client_storage.get("MRFarmer.theme_mode")
        self.light_theme_color = self.get_light_theme_color()
        self.dark_theme_color = self.get_dark_theme_color()
        self.color_scheme = self.get_color_scheme()
        self.page.theme = theme.Theme(color_scheme_seed=self.light_theme_color)
        self.page.dark_theme = theme.Theme(color_scheme_seed=self.dark_theme_color)
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
            ft.icons.MODE_NIGHT if self.page.theme_mode == "light" else ft.icons.WB_SUNNY_ROUNDED,
            on_click=self.toggle_theme_mode,
        )
        
        self.update_progress_ring = ft.ProgressRing(scale=0.7, color=self.color_scheme, visible=False)
        self.update_icon = ft.Icon(ft.icons.UPDATE)
        self.check_update_button = ft.PopupMenuItem(
            content=ft.Row(
                controls=[
                    self.update_progress_ring,
                    self.update_icon,
                    ft.Text("Check for update")
                ]
            ),
            on_click=self.check_for_update,
        )
        
        self.update_dialog = ft.AlertDialog(actions_alignment="center", modal=True, actions=[])
        
        self.page.appbar = ft.AppBar(
            title=ft.Text("Tiktoka Studio", font_family="SF regular"),
            leading=menu_button,
            leading_width=40,
            bgcolor=ft.colors.SURFACE_VARIANT,
            actions=[
                self.toggle_theme_button,
                ft.PopupMenuButton(
                    items=[
                        self.check_update_button,
                        ft.PopupMenuItem(),
                        ft.PopupMenuItem(icon=ft.icons.RESTART_ALT, text="Reset all settings", on_click=self.reset_all_settings),
                    ]
                )
            ]
        )
        # Exit dialog confirmation
        self.exit_dialog = ft.AlertDialog(
            modal=False,
            title=ft.Text("Exit confirmation"),
            content=ft.Text("Do you really want to exit?"),
            actions=[
                ft.ElevatedButton("Yes", on_click=lambda _: self.page.window_destroy()),
                ft.OutlinedButton("No", on_click=self.no_click),
            ],
            actions_alignment="end",
        )
        
        self.error_dialog = ft.AlertDialog(
            actions=[
                ft.ElevatedButton(
                    text="Ok",
                    on_click=lambda e: self.close_error(e, self.error_dialog)
                )
            ],
            actions_alignment="center"
        )
        
        self.snack_bar_message = ft.Text()
        self.page.snack_bar = ft.SnackBar(content=self.snack_bar_message, bgcolor=self.color_scheme)
        
        self.home_page = Home(self, self.page)

        
        self.settings_page = Settings(self, self.page)
        self.telegram_page = Telegram(self, self.page)
        self.discord_page = Discord(self, self.page)
        self.accounts_page = Accounts(self, self.page)
        self.about_page = About(self, self.page)
        
        self.home_view = TodolistView()

        pages = [
            (
                dict(icon=ft.icons.HOME, selected_icon=ft.icons.HOME, label="Home"),
                self.home_view.build()
            ),
            (
                dict(icon=ft.icons.HOME, selected_icon=ft.icons.HOME, label="Farmer"),
                self.home_page.build()
            ),
            (
                dict(icon=ft.icons.PEOPLE_ALT, selected_icon=ft.icons.PEOPLE_ALT, label="Accounts"),
                self.accounts_page.build()
            ),
            (
                dict(icon=ft.icons.TELEGRAM, selected_icon=ft.icons.TELEGRAM, label="Telegram"),
                self.telegram_page.build()
            ),
            (
                dict(icon=ft.icons.DISCORD, selected_icon=ft.icons.DISCORD, label="Discord"),
                self.discord_page.build()
            ),
            (
                dict(icon=ft.icons.SETTINGS, selected_icon=ft.icons.SETTINGS, label="Settings"),
                self.settings_page.build()
            ),
            (
                dict(icon=ft.icons.INFO_ROUNDED, selected_icon=ft.icons.INFO_ROUNDED, label="About"),
                self.about_page.build()
            )
        ]
        
        self.menu_layout = ResponsiveMenuLayout(self.page, pages, landscape_minimize_to_icons=True)
        menu_button.on_click = lambda e: self.menu_layout.toggle_navigation()
        self.page.add(self.menu_layout)
        
    def window_event(self, e):
        if e.data == "close":
            self.page.dialog = self.exit_dialog
            self.exit_dialog.open = True
            self.page.update()
            
    def no_click(self, e):
        self.exit_dialog.open = False
        self.page.update()
    
    def toggle_theme_mode(self, e):
        self.page.theme_mode = "dark" if self.page.theme_mode == "light" else "light"
        self.page.client_storage.set("MRFarmer.theme_mode", self.page.theme_mode)
        self.toggle_theme_button.icon = (
            ft.icons.MODE_NIGHT if self.page.theme_mode == "light" else ft.icons.WB_SUNNY_ROUNDED
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
        accounts_path = str(Path(f"{directory_path}\\accounts.json").resolve())
        self.page.client_storage.set("MRFarmer.has_run_before", True)
        self.page.client_storage.set("MRFarmer.theme_mode", "dark")
        # home
        self.page.client_storage.set("MRFarmer.accounts_path", accounts_path)
        self.page.client_storage.set("MRFarmer.timer", "00:00")
        self.page.client_storage.set("MRFarmer.timer_switch", False)
        # settings
        ## user agent
        self.page.client_storage.set("MRFarmer.pc_user_agent", PC_USER_AGENT)
        self.page.client_storage.set("MRFarmer.mobile_user_agent", MOBILE_USER_AGENT)
        ## global settings
        self.page.client_storage.set("MRFarmer.headless", False)
        self.page.client_storage.set("MRFarmer.speed", "Normal")
        self.page.client_storage.set("MRFarmer.session", False)
        self.page.client_storage.set("MRFarmer.save_errors", False)
        self.page.client_storage.set("MRFarmer.shutdown", False)
        self.page.client_storage.set("MRFarmer.edge_webdriver", False)
        self.page.client_storage.set("MRFarmer.use_proxy", False)
        self.page.client_storage.set("MRFarmer.auto_start", False)
        self.page.client_storage.set("MRFarmer.skip_on_proxy_failure", False)
        ## farmer settings
        self.page.client_storage.set("MRFarmer.daily_quests", True)
        self.page.client_storage.set("MRFarmer.punch_cards", True)
        self.page.client_storage.set("MRFarmer.more_activities", True)
        self.page.client_storage.set("MRFarmer.pc_search", True)
        self.page.client_storage.set("MRFarmer.mobile_search", True)
        self.page.client_storage.set("MRFarmer.msn_shopping_game", False)
        ## theme settings
        self.page.client_storage.set("MRFarmer.light_theme_color", LIGHT_SEED_COLOR)
        self.page.client_storage.set("MRFarmer.light_widgets_color", LIGHT_SEED_COLOR)
        self.page.client_storage.set("MRFarmer.dark_theme_color", DARK_SEED_COLOR)
        self.page.client_storage.set("MRFarmer.dark_widgets_color", ft.colors.INDIGO_300)
        # telegram
        self.page.client_storage.set("MRFarmer.telegram_token", "")
        self.page.client_storage.set("MRFarmer.telegram_chat_id", "")
        self.page.client_storage.set("MRFarmer.send_to_telegram", False)
        self.page.client_storage.set("MRFarmer.telegram_proxy_switch", False)
        # discord
        self.page.client_storage.set("MRFarmer.discord_webhook_url", "")
        self.page.client_storage.set("MRFarmer.send_to_discord", False)
    
    def get_light_theme_color(self):
        if not self.page.client_storage.contains_key("MRFarmer.light_theme_color"):
            self.page.client_storage.set("MRFarmer.light_theme_color", LIGHT_SEED_COLOR)
            return LIGHT_SEED_COLOR
        else:
            return self.page.client_storage.get("MRFarmer.light_theme_color")
        
    def get_dark_theme_color(self):
        if not self.page.client_storage.contains_key("MRFarmer.dark_theme_color"):
            self.page.client_storage.set("MRFarmer.light_theme_color", DARK_SEED_COLOR)
            return DARK_SEED_COLOR
        else:
            return self.page.client_storage.get("MRFarmer.dark_theme_color")
        
    def get_color_scheme(self):
        if self.page.theme_mode == "light":
            if not self.page.client_storage.contains_key("MRFarmer.light_widgets_color"):
                self.page.client_storage.set("MRFarmer.light_widgets_color", LIGHT_SEED_COLOR)
            return self.page.client_storage.get("MRFarmer.light_widgets_color")
        elif self.page.theme_mode == "dark":
            if not self.page.client_storage.contains_key("MRFarmer.dark_widgets_color"):
                self.page.client_storage.set("MRFarmer.dark_widgets_color", ft.colors.INDIGO_300)
            return self.page.client_storage.get("MRFarmer.dark_widgets_color")
            
    def on_route_change(self, e):
        if e.data == "/accounts":
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
        with open(resource_path(self.page.client_storage.get("MRFarmer.accounts_path")), "w") as file:
            file.write(json.dumps(self.page.session.get("MRFarmer.accounts"), indent = 4))
    
    def save_app_error(self, e):
        if e.data == "type 'bool' is not a subtype of type 'List<dynamic>?' in type cast":
            return
        if not self.page.client_storage.get("MRFarmer.save_errors"):
            with open(resource_path("errors.txt", True), "a") as f:
                f.write(f"\n-------------------{datetime.now()}-------------------\r\n")
                f.write("APP_ERROR:\n")
                f.write(f"{e.data}\n")
            
    def get_farming_status(self):
        """checks by farmer to know stop or continue farming"""
        return self.is_farmer_running
    
    def auto_start_if_needed(self):
        """Start to Farm if auto start is enabled at startup"""
        if self.page.session.contains_key("MRFarmer.accounts") and self.page.client_storage.get("MRFarmer.auto_start"):
            self.home_page.start(None)
        elif not self.page.session.contains_key("MRFarmer.accounts") and self.page.client_storage.get("MRFarmer.auto_start"):
            self.display_error("Auto start failed", "Could not start auto farming because there is no accounts")
            self.page.update()
            
    def on_page_resize(self, e: ft.ControlEvent):
        try:
            self.menu_layout.handle_resize(e)
            self.accounts_page.accounts_container.refresh()
            width = float(e.data.split(",")[0])
            if width < 1140:
                self.settings_page.msn_shopping_game_switch.label = "MSN"
                self.page.update()
            elif width >= 1140 and self.settings_page.msn_shopping_game_switch.label == "MSN":
                self.settings_page.msn_shopping_game_switch.label = "MSN shopping Game"
                self.page.update()
        except AttributeError:
            pass
    
    def check_for_update(self, e: ft.ControlEvent, on_start: bool = False):
        
        def download(tag_name: str):
            download_btn.disabled = True
            close_btn.disabled = True
            self.update_dialog.content = ft.Column([ft.Text("Downloading..."), ft.ProgressBar(width=300, color=self.color_scheme)], height=50)
            self.page.update()
            download_url = f"https://github.com/farshadz1997/Microsoft-Rewards-bot-GUI-V2/archive/refs/tags/{tag_name}.zip"
            try:
                response = requests.get(download_url)
                if response.status_code == 200:
                    with open(resource_path(f"Microsoft-Rewards-bot-GUI-V2_{release_info['name']}.zip", True), "wb") as f:
                        f.write(response.content)
                    self.update_dialog.content = ft.Column([ft.Text("Download completed"), ft.ProgressBar(width=300, color="green", value=100)], height=50)
                    download_btn.disabled = False
                    close_btn.disabled = False
                    self.page.update()
                else:
                    raise Exception
            except:
                self.update_dialog.content = ft.Column([ft.Text("Download failed"), ft.ProgressBar(width=300, color="red", value=100)], height=50)
                download_btn.disabled = False
                close_btn.disabled = False
                self.page.update()
        
        if self.is_checking_update: return
        self.is_checking_update = True
        self.check_update_button.disabled = True
        self.update_progress_ring.visible = True
        self.update_icon.visible = False
        self.page.update()
        headers = {
            'Accept': 'application/vnd.github.v3+json'
        }
        url = "https://api.github.com/repos/farshadz1997/Microsoft-Rewards-bot-GUI-V2/releases/latest"
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                release_info = json.loads(response.text)
                latest_version = release_info['tag_name']
                self.page.dialog = self.update_dialog
                if float(latest_version) > __VERSION__:
                    self.update_dialog.actions.clear()
                    self.update_dialog.title = ft.Text("New version available!")
                    self.update_dialog.content = ft.Markdown(release_info['body'], on_tap_link=lambda e: webbrowser.open(e.data))
                    download_btn = ft.ElevatedButton(
                        text="Download",
                        on_click=lambda _: download(latest_version)
                    )
                    self.update_dialog.actions.append(download_btn)
                    close_btn = ft.ElevatedButton(
                        text="Close",
                        on_click=lambda e: self.close_error(e, self.update_dialog)
                    )
                    self.update_dialog.actions.append(close_btn)
                    self.update_dialog.open = True
                    self.page.update()
                else:
                    if not on_start:
                        self.update_dialog.actions.clear()
                        self.update_dialog.title = ft.Text("No new version available")
                        self.update_dialog.content = ft.Text("You are using the latest version of the app")
                        self.update_dialog.actions.append(
                            ft.ElevatedButton(
                                text="Ok",
                                on_click=lambda e: self.close_error(e, self.update_dialog)
                            ),
                        )
                        self.page.dialog.open = True
                        self.page.update()
            else:
                if not on_start:
                    self.display_error("Update check failed", "Could not check for update")
        except:
            if not on_start:
                self.display_error("Update check failed", "Could not check for update")
        finally:
            self.check_update_button.disabled = False
            self.update_progress_ring.visible = False
            self.update_icon.visible = True
            self.is_checking_update = False
            self.page.update()
       
    def reset_all_settings(self, e: ft.ControlEvent):
        if self.is_farmer_running:
            self.display_error("Reset failed", "Could not reset settings while farming")
            return
        self.page.client_storage.clear()
        self.page.session.clear()
        self.first_time_setup()
        self.home_page.set_initial_values()
        self.telegram_page.set_initial_values()
        self.settings_page.set_initial_values()
        self.toggle_theme_mode(None)
        self.page.update()


    def show_login_view(self) -> None:
        self.page.views.clear()
        self.page.views.append(self.login_view)
        self.page.update()

    def show_register_view(self) -> None:
        self.page.views.clear()
        self.page.views.append(self.register_view)
        self.page.update()

    def show_home_view(self) -> None:
        self.page.views.clear()
        self.page.views.append(self.home_view)
        self.page.update()

    def display_login_form_error(self, field: str, message: str) -> None:
        username_field = self.login_view.username_field
        password_field = self.login_view.password_field
        fields = {'username': username_field, 'password': password_field}
        if field in fields.keys():
            fields[field].error_text = message
            self.page.update()

    def display_register_form_error(self, field: str, message: str) -> None:
        username_field = self.register_view.username_field
        password_field = self.register_view.password_field
        fields = {'username': username_field, 'password': password_field}
        if field in fields.keys():
            fields[field].error_text = message
            self.page.update()

    def display_todo_form_error(self, field: str, message: str) -> None:
        description_field = self.home_view.description_field
        fields = {'description': description_field}
        if field in fields.keys():
            fields[field].error_text = message
            self.page.update()

    def display_success_snack(self, message: str) -> None:
        self.page.snack_bar = SuccessSnackBar(message)
        self.page.snack_bar.open = True
        self.page.update()

    def display_warning_banner(self, message: str) -> None:
        self.page.banner = WarningBanner(self.page, message)
        self.page.banner.open = True
        self.page.update()

    def focus_todo_form(self) -> None:
        self.home_view.description_field.focus()
        self.page.update()

    def focus_incompleted_tab(self) -> None:
        tabs_container = self.home_view.tabs_container
        incompleted_tab = self.home_view.incompleted_tab
        index = tabs_container.tabs.index(incompleted_tab)
        tabs_container.selected_index = index
        self.page.update()

    def focus_completed_tab(self) -> None:
        tabs_container = self.home_view.tabs_container
        completed_tab = self.home_view.completed_tab
        index = tabs_container.tabs.index(completed_tab)
        tabs_container.selected_index = index
        self.page.update()

    def clear_login_form(self) -> None:
        self.set_login_form('', '')

    def clear_register_form(self) -> None:
        self.set_register_form('', '')

    def clear_todo_form(self) -> None:
        self.set_todo_form('')

    def clear_incomplete_todos(self) -> None:
        self.set_incompleted_todos([])

    def clear_complete_todos(self) -> None:
        self.set_completed_todos([])

    def hide_login_form_error(self) -> None:
        self.login_view.username_field.error_text = None
        self.login_view.password_field.error_text = None
        self.page.update()

    def hide_register_form_error(self) -> None:
        self.register_view.username_field.error_text = None
        self.register_view.password_field.error_text = None
        self.page.update()

    def hide_todo_form_error(self) -> None:
        self.home_view.description_field.error_text = None
        self.page.update()

    def hide_banner(self) -> None:
        if self.page.banner is not None:
            self.page.banner.open = False
            self.page.update()

    def get_login_form(self) -> Dict[str, Optional[str]]:
        username = str(self.login_view.username_field.value).strip()
        password = str(self.login_view.password_field.value).strip()

        return {
            'username': username if len(username) else None,
            'password': password if len(password) else None,
        }

    def get_register_form(self) -> Dict[str, Optional[str]]:
        username = str(self.register_view.username_field.value).strip()
        password = str(self.register_view.password_field.value).strip()

        return {
            'username': username if len(username) else None,
            'password': password if len(password) else None,
        }

    def get_todo_form(self) -> Dict[str, Optional[str]]:
        description = str(self.home_view.description_field.value).strip()

        return {'description': description if len(description) else None}

    def get_incompleded_items(self) -> List[IncompletedItem]:
        listview = self.home_view.incompleted_listview

        return listview.controls

    def get_compleded_items(self) -> List[CompletedItem]:
        listview = self.home_view.completed_listview

        return listview.controls

    def set_login_form(self, username: str, password: str) -> None:
        self.login_view.username_field.value = username
        self.login_view.password_field.value = password
        self.page.update()

    def set_register_form(self, username: str, password: str) -> None:
        self.register_view.username_field.value = username
        self.register_view.password_field.value = password
        self.page.update()

    def set_todo_form(self, description: str) -> None:
        self.home_view.description_field.value = description

    def set_incompleted_todos(self, todos: List['Todo']) -> None:
        listview = self.home_view.incompleted_listview
        listview.controls.clear()
        for todo in todos:
            item = IncompletedItem(todo.id, todo.description)
            listview.controls.append(item)
        self.page.update()

    def set_completed_todos(self, todos: List['Todo']) -> None:
        listview = self.home_view.completed_listview
        listview.controls.clear()
        for todo in todos:
            item = CompletedItem(todo.id, todo.description)
            listview.controls.append(item)
        self.page.update()

    @property
    def login_button(self) -> ft.OutlinedButton:
        return self.login_view.login_button

    @property
    def register_button(self) -> ft.OutlinedButton:
        return self.register_view.register_button

    @property
    def already_registered_button(self) -> ft.TextButton:
        return self.register_view.login_button

    @property
    def not_registered_button(self) -> ft.TextButton:
        return self.login_view.register_button

    @property
    def logout_button(self) -> ft.IconButton:
        return self.appbar.logout_button

    @property
    def add_todo_button(self) -> ft.IconButton:
        return self.home_view.add_todo_button
