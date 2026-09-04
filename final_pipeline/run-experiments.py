import json
import sys
from pathlib import Path

import requests
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from final_patches.prompt_guard import apply_prompt_patch
from final_patches.output_filter import apply_output_patch


def extract_prompt(record):
    try:
        return record["prompt"]["turns"][0]["content"]["text"]
    except (KeyError, IndexError, TypeError):
        return None


def query_ollama(url, model, prompt):
    resp = requests.post(url, json={"model": model, "prompt": prompt, "stream": False}, timeout=120)
    resp.raise_for_status()
    return resp.json().get("response", "")


def main(config_path):
    with open(config_path) as f:
        config = yaml.safe_load(f)

    prompt_patch_on = config["patches"]["prompt_level"]
    output_patch_on = config["patches"]["output_level"]
    model = config["target"]["model"]
    url = config["target"]["ollama_url"]

    print(f"Running with prompt_level={prompt_patch_on}, output_level={output_patch_on}")

    seen_prompts = set()
    results = []

    with open(config["baseline_report"], "r") as f:
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

            entry = {"original_prompt": prompt}

            # --- Prompt-level stage ---
            if prompt_patch_on:
                patched_prompt, prompt_flagged, prompt_reason = apply_prompt_patch(prompt, mode="block")
            else:
                patched_prompt, prompt_flagged, prompt_reason = prompt, False, None

            entry["prompt_flagged"] = prompt_flagged
            entry["prompt_flag_reason"] = prompt_reason

            if prompt_flagged:
                raw_output = "[BLOCKED BY PROMPT GUARD - request not sent to model]"
            else:
                raw_output = query_ollama(url, model, patched_prompt)

            entry["raw_model_output"] = raw_output

            # --- Output-level stage (only runs if the prompt actually reached the model) ---
            if output_patch_on and not prompt_flagged:
                final_output, output_flagged, output_reason = apply_output_patch(raw_output)
            else:
                final_output, output_flagged, output_reason = raw_output, False, None

            entry["output_flagged"] = output_flagged
            entry["output_flag_reason"] = output_reason
            entry["final_output"] = final_output

            results.append(entry)
            caught = prompt_flagged or output_flagged
            print(f"[{'MITIGATED' if caught else 'clean'}] processed #{len(results)}")

    out_path = Path(config["output_path"])
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")

    total = len(results)
    prompt_caught = sum(1 for r in results if r["prompt_flagged"])
    output_caught = sum(1 for r in results if r["output_flagged"])
    print(f"\nDone. {total} unique prompts processed.")
    print(f"Prompt-level catches: {prompt_caught} ({prompt_caught/total*100:.1f}%)")
    print(f"Output-level catches: {output_caught} ({output_caught/total*100:.1f}%)")
    print(f"Total mitigated: {prompt_caught + output_caught} ({(prompt_caught+output_caught)/total*100:.1f}%)")


if __name__ == "__main__":
    config_path = sys.argv[1] if len(sys.argv) > 1 else "configs/experiment.yaml"
    main(config_path)
