import os
import subprocess
import winreg

def get_user_environment_variable(name):
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            r'Environment') as key:
            value, _ = winreg.QueryValueEx(key, name)
            return value
    except FileNotFoundError:
        return None

def set_env_variables(env_vars: dict):
    for key, value in env_vars.items():
        os.environ[key] = value
        print(f"Set {key}={value}")
        subprocess.run(['setx', key, value])

if __name__ == "__main__":
    # Define your environment variables here
    env_vars_to_set = {
        "SLACK_USER_TOKEN": "",
        "SLACK_BOT_TOKEN": "",
        "SLACK_SIGNING_SECRET": "",
        "SLACK_CLIENT_ID":"",
    }

    set_env_variables(env_vars_to_set)

    # Example: Use them in the same session
    print("\nVerifying environment variables:")
    for key in env_vars_to_set:
        print(f"{key} = {os.getenv(key)}")
