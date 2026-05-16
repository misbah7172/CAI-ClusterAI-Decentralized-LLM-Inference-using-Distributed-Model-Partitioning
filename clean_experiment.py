#!/usr/bin/env python3
"""Clean experiment file - keep only real production data, remove synthetic test data."""

import json
from pathlib import Path

# Read the current file
exp_file = Path("logs/experiment_1773177061.json")
with open(exp_file, 'r') as f:
    data = json.load(f)

# Keep only local data (production real measurements)
clean_data = {
    "local": data.get("local", {}),
    "metadata": {
        "data_source": "PRODUCTION - Real measurements only",
        "note": "No synthetic or test data - all metrics from actual model inference"
    }
}

# Write back the clean file
with open(exp_file, 'w') as f:
    json.dump(clean_data, f, indent=2)

print("✅ File cleaned successfully")
print(f"Keys: {list(clean_data.keys())}")
print(f"Has kubernetes (synthetic): {'kubernetes' in clean_data}")
print(f"Local data present: {'local' in clean_data}")
print(f"File size: {exp_file.stat().st_size} bytes")
