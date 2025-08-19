import winreg

def get_user_environment_variable(name):
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            r'Environment') as key:
            value, _ = winreg.QueryValueEx(key, name)
            return value
    except FileNotFoundError:
        return None

