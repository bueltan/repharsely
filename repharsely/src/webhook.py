from flask import Flask, request, json
from repharsely.src.os_env import get_user_environment_variable
from repharsely.src.ollama_llm_grammar_translator import translate_and_improve
from threading import Thread
import requests
app = Flask(__name__)


@app.route("/slack/cmd_nice", methods=["POST"])
def handle_command():
    data = request.form
    trigger_id = data.get("trigger_id")
    channel_id = data.get("channel_id")
    original_text = data.get("text")

    # Start background thread
    Thread(target=process_command, args=(trigger_id, channel_id, original_text)).start()

    # Respond immediately to avoid timeout
    return "", 200

def process_command(trigger_id, channel_id, original_text):
    original_text = "Translate: " + original_text
    modified_text = translate_and_improve(original_text)
    open_edit_modal(trigger_id, channel_id, modified_text)


SLACK_USER_TOKEN = get_user_environment_variable("SLACK_USER_TOKEN")
SLACK_API_URL = "https://slack.com/api/views.open"

def open_edit_modal(trigger_id, channel_id, original_text):
    headers = {
        "Authorization": f"Bearer {SLACK_USER_TOKEN}",
        "Content-Type": "application/json",
    }

    modal_view = {
        "trigger_id": trigger_id,
        "view": {
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
                        "initial_value": original_text
                    },
                    "label": {"type": "plain_text", "text": "Edit your message"}
                }
            ]
        }
    }

    response = requests.post(SLACK_API_URL, headers=headers, json=modal_view)
    return response.json()

@app.route("/slack/interactions", methods=["POST"])
def handle_view_submission():
    """
    Handle the submission of the modal form
    """
    payload = request.form.to_dict() 

    payload_data = json.loads(payload.get('payload', '{}')) 
    
    values = payload_data["view"]["state"]["values"]
    edited_text = values["message_input"]["message_text"]["value"]
    channel_id = payload_data["view"]["private_metadata"]

    send_message_as_user(channel_id, edited_text)
    
    return "", 200  

def send_message_as_user(channel_id, text,):
    url = "https://slack.com/api/chat.postMessage"
    headers = {
        "Authorization": f"Bearer {SLACK_USER_TOKEN}",
        "Content-Type": "application/json",
    }
    data = {
        "channel": channel_id,
        "text": text,
        "as_user": True,
    }

    response = requests.post(url, headers=headers, json=data)
    return response.json()

def get_latest_messages(channel_id, limit=5):
    url = "https://slack.com/api/conversations.history"
    headers = {
        "Authorization": f"Bearer {SLACK_USER_TOKEN}",
    }
    params = {
        "channel": channel_id,
        "limit": limit,
    }

    response = requests.get(url, headers=headers, params=params)
    data = response.json()

    return data

if __name__ == "__main__":
    app.run(port=5000)