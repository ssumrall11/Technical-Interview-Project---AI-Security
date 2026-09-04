import json
import sys
from pathlib import Path
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from rough_patches.output_filter import apply_output_patch

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


def main(baseline_report_path, output_path):
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

            # NOTE: no prompt-level patch here — every prompt goes straight
            # to the model, unmodified. This isolates the output filter's
            # standalone effectiveness.
            raw_output = query_ollama(prompt)
            patched_output, was_flagged, reason = apply_output_patch(raw_output)

            results.append({
                "prompt": prompt,
                "raw_model_output": raw_output,
                "was_flagged": was_flagged,
                "flag_reason": reason,
                "final_output": patched_output,
            })
            print(f"[{'CAUGHT' if was_flagged else 'missed'}] processed #{len(results)}")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")

    caught = sum(1 for r in results if r["was_flagged"])
    print(f"\nDone. {len(results)} unique prompts processed, all sent unmodified to the model.")
    print(f"{caught} injections caught by output filter alone ({caught/len(results)*100:.1f}%).")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python rough_pipeline/run_output_only.py <baseline_report.jsonl> <output.jsonl>")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
