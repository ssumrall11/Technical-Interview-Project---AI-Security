from flask import Flask, request, jsonify
import requests
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from final_patches.prompt_guard import apply_prompt_patch
from final_patches.output_filter import apply_output_patch

app = Flask(__name__)
OLLAMA_GENERATE_URL = "http://localhost:11435/api/generate"
OLLAMA_CHAT_URL = "http://localhost:11435/api/chat"
MODEL = "llama3.2"


def run_patches(prompt):
    """Shared patch logic for both endpoints."""
    patched_prompt, prompt_flagged, _ = apply_prompt_patch(prompt, mode="block")
    if prompt_flagged:
        return "I can't help with that request."
    resp = requests.post(
        OLLAMA_GENERATE_URL,
        json={"model": MODEL, "prompt": patched_prompt, "stream": False},
        timeout=120,
    )
    raw_output = resp.json().get("response", "")
    response_text, _, _ = apply_output_patch(raw_output)
    return response_text


@app.route("/api/generate", methods=["POST"])
def generate():
    data = request.get_json()
    prompt = data.get("prompt", "")
    response_text = run_patches(prompt)
    return jsonify({"model": MODEL, "response": response_text, "done": True})


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json()
    messages = data.get("messages", [])
    # Take the last user message as the prompt
    prompt = messages[-1]["content"] if messages else ""
    response_text = run_patches(prompt)
    return jsonify({
        "model": MODEL,
        "message": {"role": "assistant", "content": response_text},
        "done": True,
    })


if __name__ == "__main__":
    app.run(port=11434)
