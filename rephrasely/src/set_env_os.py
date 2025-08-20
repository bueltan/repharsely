
""" Sets environment variables from a YAML file, with OS-specific persistence.
- On Windows, uses `setx` to persist for future sessions.
- On Linux/macOS, appends `export KEY="value"` to the user's shell rc file.
- Ensures idempotency by replacing existing entries.
- Validates YAML structure and env var names.
"""
import os
import re
import subprocess
import platform
from pathlib import Path

try:
    import yaml  
except ImportError as e:
    raise SystemExit("Missing dependency: install with `pip install pyyaml`") from e


def load_env_from_yaml(yaml_path: str | os.PathLike) -> dict[str, str]:
    """
    Reads a YAML file containing a flat mapping of env vars:
      XAI_API_KEY: "..."
      SLACK_USER_TOKEN: "..."
    Returns a dict[str, str].
    """
    p = Path(yaml_path).expanduser().resolve()
    if not p.exists():
        raise FileNotFoundError(f"YAML file not found: {p}")

    with p.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    if not isinstance(data, dict):
        raise ValueError("YAML root must be a mapping of KEY: VALUE")

    # Coerce all values to strings (env vars must be strings)
    env_vars = {str(k): "" if v is None else str(v) for k, v in data.items()}

    # Basic key sanity: uppercase + _ and alnum (relaxed but safe)
    bad = [k for k in env_vars if not re.fullmatch(r"[A-Z0-9_]+", k)]
    if bad:
        raise ValueError(f"Invalid env var names: {bad} (use A–Z, 0–9, and _)")

    return env_vars


def _detect_shell_rc() -> Path:
    """
    Picks the most likely shell rc file for persistence on *nix.
    Preference: current SHELL -> ~/.zshrc or ~/.bashrc; fallback to ~/.profile
    """
    shell = os.environ.get("SHELL", "")
    home = Path.home()
    if "zsh" in shell:
        return home / ".zshrc"
    if "bash" in shell:
        # If login shells load .bash_profile on macOS; but .bashrc is a fine place for exports.
        return home / ".bashrc"
    # Fallback that most shells source at login
    return home / ".profile"


def _ensure_export_line(rc_path: Path, key: str, value: str):
    """
    Idempotently ensure `export KEY=value` exists in rc_path.
    - Replaces an existing line for KEY.
    - Appends if not present.
    """
    rc_path.touch(exist_ok=True)
    content = rc_path.read_text(encoding="utf-8")

    # Pattern for lines like: export KEY=... (allow quotes/spaces)
    pat = re.compile(rf"^export\s+{re.escape(key)}=.*$", re.MULTILINE)

    new_line = f'export {key}="{value}"'

    if pat.search(content):
        content = pat.sub(new_line, content)
    else:
        if content and not content.endswith("\n"):
            content += "\n"
        content += new_line + "\n"

    rc_path.write_text(content, encoding="utf-8")


def set_env_variables(env_vars: dict[str, str], persist: bool = True):
    """
    Sets env vars in current process and (optionally) persists them.
    - Windows: uses `setx` per variable (future sessions only).
    - Linux/macOS: writes `export KEY="value"` to the shell rc file.
    """
    for key_env, value in env_vars.items():
        # In-process for current Python & its children
        os.environ[key_env] = value
        print(f"Set {key_env} (in-process)")

        if not persist:
            continue

        system = platform.system()
        if system == "Windows":
            # setx does not affect the *current* process; future shells will have it
            completed = subprocess.run(
                ["setx", key_env, value],
                capture_output=True,
                text=True,
                shell=True , # ensures setx is found in cmd on some setups
                check= True,
            )
            if completed.returncode != 0:
                raise RuntimeError(
                    f"Failed to persist {key_env} with setx: {completed.stderr.strip()}"
                )
            print(f"Persisted {key_env} via setx")
        else:
            rc = _detect_shell_rc()
            _ensure_export_line(rc, key_env, value)
            print(f'Persisted {key_env} in "{rc}"')


if __name__ == "__main__":
    # --- Configure your YAML path here ---
    YAML_PATH = "./secrets_envs.yml"  # e.g., ~/.config/myapp/env.yml

    # Example YAML structure:
    # XAI_API_KEY: "..."
    # SLACK_USER_TOKEN: "..."
    # SLACK_BOT_TOKEN: "..."
    # SLACK_SIGNING_SECRET: "..."
    # SLACK_CLIENT_ID: "..."

    env_vars_to_set = load_env_from_yaml(YAML_PATH)

    # Set & persist
    set_env_variables(env_vars_to_set, persist=True)

    # Verify in the current Python process (won't print values to avoid leaking secrets)
    print("\nVerifying (current process):")
    for key in env_vars_to_set:
        val = os.getenv(key)
        print(f"{key} is {'SET' if (val is not None and val != '') else 'EMPTY/UNSET'}")
