import flet as ft
from src.ui import UserInterface


def main() -> None:
    # ft.app(target=Application)
    ft.app(target=UserInterface, view=ft.WEB_BROWSER)


if __name__ == '__main__':
    main()
