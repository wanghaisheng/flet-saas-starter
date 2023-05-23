"""
This is our controller layer.
"""
# python
from typing import Any
from typing import Optional
from typing import TYPE_CHECKING

# local
from src.utils import constants
from src.core.model import AlreadyRegistered
from src.core.model import NotRegistered
from src.core.model import RequiredField
from src.core.model import DataBase
from src.core.model import Todo
from src.core.model import User

if TYPE_CHECKING:
    from src.core.app_layout import UserInterface


class Handler:
    def __init__(self, application: 'UserInterface') -> None:
        """This class will configure the application widgets events."""
        self.application = application

        # yes, here is where our database will be started.
        self.database = DataBase(constants.DB_NAME)
        self.user: Optional[User] = None

        # ok, lets configure widgets events.
        self.application.login_button.on_click = lambda e: self.login_click()
        self.application.register_button.on_click = (
            lambda e: self.register_click()
        )
        self.application.already_registered_button.on_click = (
            lambda e: self.already_registered_click()
        )
        self.application.not_registered_button.on_click = (
            lambda e: self.not_registered_click()
        )
        self.application.logout_button.on_click = lambda e: self.logout_click()
        self.application.add_todo_button.on_click = (
            lambda e: self.add_todo_click()
        )

    def login_click(self) -> None:
        """Will try login the user."""
        try:
            # 1) first, we get the fields values.
            form = self.application.get_login_form()
            username = form.get('username')
            password = form.get('password')

            # 2) second, lets hide all messages.
            self.application.hide_banner()
            self.application.hide_login_form_error()

            # 3) third, checking if this user exists.
            user = self.database.login_user(username, password)

            # 4) fourth, users exists so lets show the home view.
            self.user = user
            self.refresh_todo_list()
            self.application.show_home_view()
            self.application.focus_todo_form()
            self.application.focus_incompleted_tab()
            self.application.display_success_snack(f'Welcome {username}')

        # ops, some required field is not informed, lets give a feedback.
        except RequiredField as error:
            self.application.display_login_form_error(error.field, str(error))

        # ops, this user not exists, lets give a feedback.
        except NotRegistered as error:
            self.application.display_login_form_error('username', str(error))

        # ok, some thing really bad hapened.
        except Exception as error:
            self.application.display_warning_banner(str(error))

    def register_click(self) -> None:
        """Will try register a new user."""
        try:
            # 1) first, we get the input.
            form = self.application.get_register_form()
            username = form.get('username')
            password = form.get('password')

            # 2) second, lets hide all messages.
            self.application.hide_banner()
            self.application.hide_register_form_error()

            # 3) third, lets try register this users.
            user = self.database.register_user(username, password)

            # 4) fourth, lets show the home view.
            self.user = user
            self.refresh_todo_list()
            self.application.show_home_view()
            self.application.focus_todo_form()
            self.application.focus_incompleted_tab()
            self.application.display_success_snack(f'Welcome {username}')

        # ops, some required field is not informed, lets give a feedback.
        except RequiredField as error:
            self.application.display_register_form_error(
                error.field, str(error)
            )

        # ops, this username is already in use, lets give a feedback.
        except AlreadyRegistered as error:
            self.application.display_register_form_error(
                error.field, str(error)
            )

        # ok, some thing really bad hapened.
        except Exception as error:
            self.application.display_warning_banner(str(error))

    def already_registered_click(self) -> None:
        """nothing in special, just show login view."""
        self.application.show_login_view()

    def not_registered_click(self) -> None:
        """nothing in special, just show register view."""
        self.application.show_register_view()

    def logout_click(self) -> None:
        """
        here some things happens.
        all formularies, listviews and others widgets that grabed data stuffs
        are cleaned and our login view will be showed.
        """
        self.application.hide_login_form_error()
        self.application.hide_register_form_error()
        self.application.hide_todo_form_error()
        self.application.clear_incomplete_todos()
        self.application.clear_complete_todos()
        self.application.clear_register_form()
        self.application.clear_login_form()
        self.application.show_login_view()

        # lets fill the login form and set our
        # current user to none.
        if self.user is not None:
            self.application.set_login_form(
                self.user.username, self.user.password
            )
            self.user = None

    def add_todo_click(self) -> None:
        """Will try register a new todo."""
        try:
            # 1) first, lets start getting the input.
            form = self.application.get_todo_form()
            description = form.get('description')

            # 2) second, hide all messages.
            self.application.hide_banner()
            self.application.hide_todo_form_error()

            # 3) third, lets register it.
            self.database.register_todo(
                description=description, completed=False, id_user=self.user.id
            )

            # 3) fourth, now we update the application.
            self.application.clear_todo_form()
            self.application.focus_todo_form()
            self.application.focus_incompleted_tab()
            self.refresh_todo_list()

        # ops, some required field is not informed, lets give a feedback.
        except RequiredField as error:
            self.application.display_todo_form_error(error.field, str(error))

        # ok, some thing really bad hapened.
        except Exception as error:
            self.application.display_warning_banner(str(error))

    def delete_item_click(self, item: Any) -> None:
        """Will try delete the item."""
        try:
            # 1) first, lets try delete this register.
            pk = item.primary_key
            todo = self.database.select_todo_by_id(pk)
            self.database.delete_todo(todo)

            # 2) second, lets update or application.
            self.refresh_todo_list()

            # 3) third, a successfully feedback.
            self.application.display_success_snack('Successfully')

        # ok, some thing really bad hapened.
        except Exception as error:
            self.application.display_warning_banner(str(error))

    def toggle_item_click(self, item: Any) -> None:
        """
        Switch a item between completed and incompleted.
        """
        pk = item.primary_key
        todo = self.database.select_todo_by_id(pk)
        todo.completed = not todo.completed
        self.database.update_todo(todo)
        self.refresh_todo_list()
        self.application.focus_incompleted_tab()
        self.application.focus_completed_tab()

        if todo.completed:
            self.application.focus_completed_tab()
        else:
            self.application.focus_incompleted_tab()

    def refresh_todo_list(self) -> None:
        """
        Ok, basicly our application will grab dinamic widgets,
        so this method will update todo list and configure theirs binds.
        """
        incompleted = self.database.filter_todos(
            completed=False, user=self.user
        )
        completed = self.database.filter_todos(completed=True, user=self.user)
        self.application.set_incompleted_todos(incompleted)
        self.application.set_completed_todos(completed)
        self.bind_todo_items()

    def bind_todo_items(self) -> None:
        """Bind incompleted and completed todo items."""
        incompleted_items = self.application.get_incompleded_items()
        completed_items = self.application.get_compleded_items()

        for item in incompleted_items:
            item.delete_button.on_click = (
                lambda e, item=item: self.delete_item_click(item)
            )
            item.complete_button.on_click = (
                lambda e, item=item: self.toggle_item_click(item)
            )

        for item in completed_items:
            item.delete_button.on_click = (
                lambda e, item=item: self.delete_item_click(item)
            )
            item.incomplete_button.on_click = (
                lambda e, item=item: self.toggle_item_click(item)
            )
