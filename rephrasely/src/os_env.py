import os
import sys

def get_user_environment_variable(name: str) -> str | None:
    """
    Retrieve a user environment variable in a cross-platform way.
    - On Windows: read from the Registry (HKCU\Environment).
    - On Unix-like systems: read from os.environ.
    """
    if sys.platform.startswith("win"):
        # pylint: disable=import-outside-toplevel
        # pylint: disable=E0401
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment") as key:
                value, _ = winreg.QueryValueEx(key, name)
                return value
        except FileNotFoundError:
            return None
        except OSError:
            return None
    else:
        # Unix (Linux, macOS, etc.)
        return os.environ.get(name)
