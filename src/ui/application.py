"""
This is or view layer.
"""
# python
from typing import Dict
from typing import List
from typing import Optional

# 3rd
import flet as ft

# local
from src.utils import constants
from src.core.handler import Handler
from src.core.model import Todo
from .app_layout import UserInterface

class ApplicationAppBar(ft.AppBar):
    def __init__(self) -> None:
        super().__init__()

        self.title = ft.Text()
        self.title.value = 'Flet Alchemy'
        self.leading = self.title

        self.logout_button = ft.IconButton()
        self.logout_button.icon = ft.icons.LOGOUT
        self.logout_button.tooltip = 'Logout'
        self.actions.append(self.logout_button)


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


class HomeView(ft.View):
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
        self.controls.append(userInterface)


class Application:
    def __init__(self, page: ft.Page) -> None:
        """This class will grab all others widgets."""
        # 1), first we create all the widgets.
        self.page = page
        self.page.title = 'Flet-Alchemy'
        self.login_view = LoginView()
        self.register_view = RegisterView()
        self.home_view = HomeView()

        # 2) now, after widgets created, we can configure their events.
        # and start the database.
        self.handler = Handler(self)

        # 3) setting the initial state.
        self.show_register_view()
        self.show_home_view()
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
        return self.home_view.appbar.logout_button

    @property
    def add_todo_button(self) -> ft.IconButton:
        return self.home_view.add_todo_button
