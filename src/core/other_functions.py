import os
import sys
import traceback
from datetime import datetime


def resource_path(relative_path: str, exc_path: bool = False) -> str:
    """Get absolute path for resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
        if exc_path:
            base_path = os.path.dirname(sys.executable)
    except AttributeError:
        base_path = os.getcwd()
    except Exception as e:
        save_error_path = os.path.join(os.getcwd(), 'errors.txt')
        tb = e.__traceback__
        tb_str = traceback.format_tb(tb)
        error = '\n'.join(tb_str).strip() + f'\n{e}'
        with open(save_error_path, 'a') as f:
            f.write(
                f'\n-------------------{datetime.now()}-------------------\r\n'
            )
            f.write(f'{error}\n')
            return

    return os.path.join(base_path, relative_path)
