import os
from flask import Flask, request, redirect
import requests


REDIRECT_URI = "https://eda7-168-196-24-204.ngrok-free.app/slack/oauth/callback"

app = Flask(__name__)

@app.route("/")
def home():
    return f'<a href="https://slack.com/oauth/v2/authorize?client_id={CLIENT_ID}&scope=chat:write&user_scope=chat:write&redirect_uri={REDIRECT_URI}">Autorizar Slack App</a>'

@app.route("/slack/oauth/callback")
def oauth_callback():
    code = request.args.get("code")
    res = requests.post(
        "https://slack.com/api/oauth.v2.access",
        data={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "code": code,
            "redirect_uri": REDIRECT_URI,
        },
    )
    data = res.json()
    user_token = data["authed_user"]["access_token"]
    return f"Tu user token: <code>{user_token}</code><br><br><strong>Guardalo, lo vas a usar para postear como vos</strong>"

if __name__ == "__main__":
    app.run(debug=True)
