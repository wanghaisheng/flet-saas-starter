"""
This is our controller layer.
"""
from typing import TYPE_CHECKING, Any, Optional

from src.core.model import (
    AlreadyRegistered,
    DataBase,
    NotRegistered,
    RequiredField,
    Todo,
    User,
)
from src.utils import constants

if TYPE_CHECKING:
    from src.ui import Application


class Handler:
    def __init__(self, application: 'Application') -> None:
        """This class will configure the application widgets events."""
        self.application = application

        # yes, here is where our database will be started.
        self.database = DataBase(constants.DB_NAME)
        self.user: Optional[User] = None

        # ok, lets configure widgets events.
        self.__bind_login_view()
        self.__bind_register_view()
        self.__bind_user_interface_view()

    def __bind_login_view(self) -> None:
        self.application.login_button.on_click = lambda e: self.login_click()

        self.application.register_button.on_click = (
            lambda e: self.register_click()
        )

    def __bind_register_view(self) -> None:
        self.application.already_registered_button.on_click = (
            lambda e: self.already_registered_click()
        )
        self.application.not_registered_button.on_click = (
            lambda e: self.not_registered_click()
        )

    def __bind_user_interface_view(self) -> None:
        self.application.logout_button.on_click = lambda e: self.logout_click()

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
            self.application.show_user_interface_view()
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
            self.application.show_user_interface_view()
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
