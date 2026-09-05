
# Technical-Interview-Project---AI-Security Setup Directions

Step 1: Install Ollama and pull the model

```bash
brew install ollama
brew services start ollama
ollama pull llama3.2
ollama run llama3.2 "say hello"  # sanity check```

Step 2: Set up Python environment and Garak
```bash
cd Technical-Interview-Project---AI-Security
python3 -m venv venv
source venv/bin/activate
pip install garak
pip install requests pyyaml flask
garak --version  # sanity check```

Step 3: Baseline Vulnerability Scan

```bash
mkdir -p results
garak --target_type ollama --target_name llama3.2 \
  --probes promptinject.HijackLongPrompt \
  --generations 1 \
  --report_prefix "$(pwd)/results/baseline"```

Step 4: Rough Draft Patching (Unconfigured)

Prompt-level only
`python rough_pipeline/run_patched.py results/baseline_report.jsonl results/patched.jsonl`

Output-level only
`python rough_pipeline/run_output_only.py results/baseline_report.jsonl results/output_only.jsonl`

Step 5: Configured Patching (Config-Driven)

Edit configs/experiment.yaml to toggle patches:
  ```bash
    patches:
      prompt_level: true/false
      output_level: true/false```

`python final_pipeline/run-experiments.py configs/experiment.yaml`

Analysis / Classification

`python analysis/classify.py`

Step 6: Garak-Native Verification (Proxy)

Terminal 1 — move Ollama off its default port
`OLLAMA_HOST=127.0.0.1:11435 ollama serve`

Terminal 2 — run the proxy on Ollama's default port
`python proxy-server.py`

Terminal 3 — run Garak (no special config needed; uses default port 11434)
```bash
garak --target_type ollama --target_name llama3.2 \
  --probes promptinject.HijackLongPrompt \
  --generations 1 \
  --report_prefix "$(pwd)/results/garak-verified"```

Cleanup (after verification)

# Ctrl+C all three tabs above, then restore normal Ollama:
`brew services start ollama`
