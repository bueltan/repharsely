import os
from flask import Flask, request, json, render_template_string, jsonify
from threading import Thread
import requests

from rephrasely.src.grok_llm_rephrasely import rephrasely_method
from rephrasely.src.os_env import get_user_environment_variable
from rephrasely.src.set_env_os import set_env_variables

app = Flask(__name__)

SLACK_API_BASE = "https://slack.com/api"
SLACK_VIEWS_OPEN = f"{SLACK_API_BASE}/views.open"
SLACK_VIEWS_UPDATE = f"{SLACK_API_BASE}/views.update"
SLACK_CHAT_POST = f"{SLACK_API_BASE}/chat.postMessage"


CLIENT_ID = get_user_environment_variable("SLACK_CLIENT_ID") or ""
CLIENT_SECRET = get_user_environment_variable("SLACK_CLIENT_SECRET") or ""
REDIRECT_URI = ( get_user_environment_variable("SLACK_REDIRECT_URI") or
                "https://rephrasely.com.ar/slack/oauth/callback")

if not CLIENT_ID or not CLIENT_SECRET:
    raise ValueError("SLACK_CLIENT_ID and SLACK_CLIENT_SECRET must be set in environment variables.")

def _auth_headers():
    token = get_user_environment_variable("SLACK_USER_TOKEN")
    if not token:
        app.logger.error("SLACK_USER_TOKEN is missing. Complete OAuth first.")
        return None
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

@app.route("/")
def home():
    """Home page with Slack app authorization link."""
    auth_url = (
        "https://slack.com/oauth/v2/authorize"
        f"?client_id={CLIENT_ID}"
        f"&scope=chat:write"
        f"&user_scope=chat:write"
        f"&redirect_uri={REDIRECT_URI}"
    )
    return render_template_string(
        '<a href="{{auth_url}}">Authorize Slack App</a>',
        auth_url=auth_url,
    )


@app.route("/slack/oauth/callback")
def oauth_callback():
    """Handles OAuth callback and displays the user token to save."""
    code = request.args.get("code")
    if not code:
        return "Missing ?code param", 400

    res = requests.post(
        "https://slack.com/api/oauth.v2.access",
        data={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "code": code,
            "redirect_uri": REDIRECT_URI,
        },
        timeout=10,
    )
    data = res.json()
    if not data.get("ok"):
        return jsonify(data), 400

    user_token = data["authed_user"]["access_token"]
    set_env_variables({"SLACK_USER_TOKEN": user_token}, persist=True)
    os.environ["SLACK_USER_TOKEN"] = user_token
    return (
        "Your user token:<br>"
        f"<code>{user_token}</code><br><br>"
        "<strong>Save this as SLACK_USER_TOKEN in your .env</strong>"
    )


# ----------------------------------------------------------


@app.route("/slack/rephrasely", methods=["POST"])
def handle_command():
    """
    Slash command entrypoint:
    1) Open a quick 'Working…' modal immediately (within 3s).
    2) Kick off background work; when done, update the modal to the editable version.
    """
    data = request.form
    trigger_id = data.get("trigger_id")
    channel_id = data.get("channel_id")
    original_text = data.get("text", "")

    # 1) Open quick "Working..." modal synchronously
    view_id = open_working_modal(trigger_id, channel_id)

    # 2) Process in background and update the modal when done
    Thread(
        target=process_and_update_modal,
        args=(view_id, channel_id, original_text),
        daemon=True,
    ).start()

    # Respond immediately to avoid timeout
    return "", 200


def process_and_update_modal(view_id: str, channel_id: str, original_text: str):
    """
    Runs LLM processing and updates the modal with the final editable content.
    """
    prompt = "Translate: " + (original_text or "")

    try:
        modified_text = rephrasely_method(prompt)
    # pylint: disable=broad-except
    except Exception as e:
        # Fallback message if LLM fails
        modified_text = f"(Error generating suggestion: {e})\n\n{prompt}"

    # Swap the modal content to the real editable view
    update_modal_with_result(view_id, channel_id, modified_text)


def open_working_modal(trigger_id: str, channel_id: str) -> str:
    """
    Open a minimal modal that shows a spinner/message quickly.
    Return the view_id so we can later call views.update.
    """
    payload = {
        "trigger_id": trigger_id,
        "view": {
            "type": "modal",
            "callback_id": "edit_and_send_message",  # keep same callback for later
            # no 'submit' here -> it's just a waiting modal
            "close": {"type": "plain_text", "text": "Cancel"},
            "private_metadata": channel_id,
            "title": {"type": "plain_text", "text": "Rephrasely"},
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": ":hourglass_flowing_sand: Working on your suggestion…",
                    },
                },
            ],
        },
    }


    r = requests.post(SLACK_VIEWS_OPEN, headers=_auth_headers(), json=payload, timeout=10)
    data = r.json()
    if not data.get("ok"):
        app.logger.error("views.open failed: %s", data)
        # Return empty; update will no-op if view_id is missing
        return ""
    # Slack returns the newly opened view under `view`
    return data["view"]["id"]


def update_modal_with_result(view_id: str, channel_id: str, suggested_text: str):
    """
    Replace the 'Working…' modal with the real editable modal using views.update.
    """
    if not view_id:
        app.logger.error("No view_id available to update modal.")
        return

    new_view = {
        "type": "modal",
        "callback_id": "edit_and_send_message",
        "title": {"type": "plain_text", "text": "Edit Message"},
        "submit": {"type": "plain_text", "text": "Send"},
        "close": {"type": "plain_text", "text": "Cancel"},
        "private_metadata": channel_id,
        "blocks": [
            {
                "type": "input",
                "block_id": "message_input",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "message_text",
                    "multiline": True,
                    "initial_value": suggested_text or "",
                },
                "label": {"type": "plain_text", "text": "Edit your message"},
            }
        ],
    }

    payload = {
        "view_id": view_id,
        "view": new_view,
    }

    r = requests.post(
        SLACK_VIEWS_UPDATE, headers=_auth_headers(), json=payload, timeout=20
    )
    if not r.ok:
        app.logger.error("views.update failed: %s", r.text)


@app.route("/slack/interactions", methods=["POST"])
def handle_view_submission():
    """
    Handle submission of the modal form (after the update).
    """
    payload = request.form.to_dict()
    payload_data = json.loads(payload.get("payload", "{}"))

    # Expect a 'view_submission'
    if payload_data.get("type") == "view_submission":
        values = payload_data["view"]["state"]["values"]
        edited_text = values["message_input"]["message_text"]["value"]
        channel_id = payload_data["view"]["private_metadata"]

        send_message_as_user(channel_id, edited_text)
        return "", 200

    # Ignore other interaction types for now
    return "", 200


def send_message_as_user(channel_id: str, text: str):
    """
    Posts the final edited message as the *user* (using your user token).
    """
    slack_user_token = get_user_environment_variable("SLACK_USER_TOKEN")

    headers = {
        "Authorization": f"Bearer {slack_user_token}",
        "Content-Type": "application/json",
    }
    data = {
        "channel": channel_id,
        "text": text,
        # Using a user token -> message is sent as that user; `as_user` is unnecessary.
    }
    response = requests.post(SLACK_CHAT_POST, headers=headers, json=data, timeout=10)
    if not response.ok:
        app.logger.error("chat.postMessage failed: %s", response.text)
    return response.json() if response.content else {}


def get_latest_messages(channel_id, limit=5):
    """
    Fetches the latest messages from a Slack channel using conversations.history.
    """
    slack_user_token = get_user_environment_variable("SLACK_USER_TOKEN")

    url = f"{SLACK_API_BASE}/conversations.history"
    headers = {"Authorization": f"Bearer {slack_user_token}"}
    params = {"channel": channel_id, "limit": limit}

    response = requests.get(url, headers=headers, params=params, timeout=10)
    data = response.json()
    return data


if __name__ == "__main__":
    app.run(port=5000)
