"""
This is or view layer.
"""
from typing import Dict, List, Optional

import flet as ft

from src.core.handler import Handler
from src.core.model import Todo
from src.ui import UserInterface
from src.utils import constants


class ApplicationAppBar(ft.AppBar):
    def __init__(self) -> None:
        super().__init__()

        self.title = ft.Text()
        self.title.value = 'TikToka-Studio'
        self.leading = self.title

        self.logout_button = ft.IconButton()
        self.logout_button.icon = ft.icons.LOGOUT
        self.logout_button.tooltip = 'Logout'
        self.actions.append(self.logout_button)


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


class Application:
    def __init__(self, page: ft.Page) -> None:
        """This class will grab all others widgets."""
        # 1), first we create all the widgets.
        self.page = page
        self.page.title = 'Flet-Alchemy'
        self.user_interface = UserInterface(self.page)
        self.login_view = LoginView()
        self.register_view = RegisterView()

        # 2) now, after widgets created, we can configure their events.
        # and start the database.
        self.handler = Handler(self)

        # 3) setting the initial state.
        self.show_login_view()
        self.set_login_form(
            constants.DEFAULT_USERNAME, constants.DEFAULT_PASSWORD
        )

    def show_login_view(self) -> None:
        self.page.views.clear()
        self.page.views.append(self.login_view)
        self.page.update()

    def show_register_view(self) -> None:
        self.page.views.clear()
        self.page.views.append(self.register_view)
        self.page.update()

    def show_user_interface_view(self) -> None:
        self.page.views.clear()
        self.page.views.append(self.user_interface)
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

    def display_success_snack(self, message: str) -> None:
        self.page.snack_bar = SuccessSnackBar(message)
        self.page.snack_bar.open = True
        self.page.update()

    def display_warning_banner(self, message: str) -> None:
        self.page.banner = WarningBanner(self.page, message)
        self.page.banner.open = True
        self.page.update()

    def clear_login_form(self) -> None:
        self.set_login_form('', '')

    def clear_register_form(self) -> None:
        self.set_register_form('', '')

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

    def set_login_form(self, username: str, password: str) -> None:
        self.login_view.username_field.value = username
        self.login_view.password_field.value = password
        self.page.update()

    def set_register_form(self, username: str, password: str) -> None:
        self.register_view.username_field.value = username
        self.register_view.password_field.value = password
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
        return self.user_interface.logout_button
