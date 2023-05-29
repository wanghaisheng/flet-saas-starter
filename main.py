from pathlib import Path
import json

import flet as ft

from src.core import resource_path
from src.ui import Application


def main():
    if not Path(resource_path("accounts.json", True)).exists():
        with open(resource_path("accounts.json", True), "w") as f:
            f.write(json.dumps([{"username": "Your Email", "password": "Your Password"}], indent=4))
    ft.app(target=Application, assets_dir=resource_path("assets"))


if __name__ == "__main__":
    main()

