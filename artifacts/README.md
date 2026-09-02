# Runtime artifacts

This directory is the local output root for generated evidence. Its contents
are intentionally ignored by Git.

Typical subdirectories are:

- `logs/`: CARLA JSONL logs and adjacent summaries;
- `runtime/`: staged Qwen images and short-lived runner state;
- `models/`: locally downloaded detector weights;
- `reports/`: generated validation and benchmark reports;
- `voice/`: generated ASR evaluation output.

Promotion-grade evidence must come from an actual run, retain its commit, seed
and configuration path, and be copied to controlled external storage or a
release package before local cleanup.
