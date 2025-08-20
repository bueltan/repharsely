import os
import sys
import json
import requests
from typing import List, Dict, Any

XAI_API_KEY =  os.getenv("XAI_API_KEY")  # set this in your env
XAI_CHAT_URL = "https://api.x.ai/v1/chat/completions"

def grok_chat(
    messages: List[Dict[str, str]],
    model: str = "grok",  # Changed to a safer default, adjust based on xAI API docs
    temperature: float = 0.0,
    stream: bool = False,
    timeout: int = 60,
) -> str:
    """
    Call x.ai (Grok) chat completions API.

    Args:
        messages: list of {"role": "system"|"user"|"assistant", "content": "..."}
        model: Model name (e.g., "grok"). Check xAI API docs for valid models.
        temperature: Controls randomness (0.0 = deterministic).
        stream: If True, streams response chunks.
        timeout: Request timeout in seconds.

    Returns:
        The full response text. If stream=True, prints chunks to stdout.

    Raises:
        RuntimeError: If XAI_API_KEY is not set.
        requests.HTTPError: If the API request fails.
    """
    if not XAI_API_KEY:
        raise RuntimeError("Missing XAI_API_KEY environment variable.")

    headers = {
        "Authorization": f"Bearer {XAI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload: Dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "stream": stream,
    }

    # Debug: Print the request payload
    print("Request Payload:", json.dumps(payload, indent=2))

    try:
        resp = requests.post(XAI_CHAT_URL, headers=headers, json=payload, stream=stream, timeout=timeout)
        # Debug: Print status and response text if not 200
        if resp.status_code != 200:
            print(f"Response Status: {resp.status_code}")
            print(f"Response Text: {resp.text}")
        resp.raise_for_status()
    except requests.HTTPError as e:
        raise requests.HTTPError(f"HTTP Error: {e}. Response: {e.response.text}")

    if not stream:
        data = resp.json()
        return data["choices"][0]["message"]["content"]

    # Streaming (Server-Sent Events)
    output = []
    for raw_line in resp.iter_lines(decode_unicode=True):
        if not raw_line:
            continue

        line = raw_line.strip()
        if line.startswith("data:"):
            line = line[len("data:"):].strip()

        if line == "[DONE]":
            break

        try:
            obj = json.loads(line)
            delta = obj.get("choices", [{}])[0].get("delta", {}).get("content", "")
            if not delta:
                delta = obj.get("choices", [{}])[0].get("text", "")
            if not delta:
                delta = obj.get("choices", [{}])[0].get("message", {}).get("content", "")
        except Exception:
            delta = line

        if delta:
            sys.stdout.write(delta)
            sys.stdout.flush()
            output.append(delta)

    return "".join(output)


def rephrasely_method(prompt: str, model: str = "grok", stream: bool = False) -> str:
    """
    Translate and improve the given prompt using Grok.
    Adjust the system prompt to your taste.
    """
    system_prompt = (
        "You are a precise translator and editor. "
        "Task: translate the user's text to clear, natural English and improve grammar, "
        "tone, and flow while preserving meaning. If the input is already in English, "
        "just improve clarity and correctness. Return only the improved text."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt},
    ]

    return grok_chat(messages=messages, model=model, temperature=0, stream=stream)


