import json
import sys
from pathlib import Path
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from rough_patches.prompt_guard import apply_prompt_patch

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3.2"


def extract_prompt(record):
    try:
        return record["prompt"]["turns"][0]["content"]["text"]
    except (KeyError, IndexError, TypeError):
        return None


def query_ollama(prompt):
    resp = requests.post(
        OLLAMA_URL, json={"model": MODEL, "prompt": prompt, "stream": False}, timeout=120
    )
    resp.raise_for_status()
    return resp.json().get("response", "")


def main(baseline_report_path, output_path, mode="block"):
    seen_prompts = set()
    results = []

    with open(baseline_report_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue

            prompt = extract_prompt(record)
            if not prompt or prompt in seen_prompts:
                continue
            seen_prompts.add(prompt)

            patched_prompt, was_flagged, reason = apply_prompt_patch(prompt, mode=mode)

            if was_flagged and mode == "block":
                model_output = "[BLOCKED BY PROMPT GUARD - request not sent to model]"
            else:
                model_output = query_ollama(patched_prompt)

            results.append({
                "original_prompt": prompt,
                "was_flagged": was_flagged,
                "flag_reason": reason,
                "patched_prompt": patched_prompt if was_flagged else None,
                "model_output": model_output,
            })
            print(f"[{'FLAGGED' if was_flagged else 'clean'}] processed #{len(results)}")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")

    flagged = sum(1 for r in results if r["was_flagged"])
    print(f"\nDone. {len(results)} unique prompts processed.")
    print(f"{flagged} flagged/blocked ({flagged/len(results)*100:.1f}%).")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python pipeline/run_patched.py <baseline_report.jsonl> <output.jsonl> [mode]")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "block")
