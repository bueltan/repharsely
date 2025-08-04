import requests

USER_TOKEN = ""  # token obtenido vía OAuth

headers = {
    "Authorization": f"Bearer {USER_TOKEN}",
    "Content-Type": "application/json",
}

payload = {
    "channel": "#general",  # ID de canal (o podés usar un nombre tipo "#general")
    "text": "Hola, este mensaje parece escrito por mí 🤫",
}

res = requests.post("https://slack.com/api/chat.postMessage", headers=headers, json=payload)
print(res.json())