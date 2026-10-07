"""Validate public candidate results and reject direct-identifier fields."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.batch import validate_public_results


path = Path(sys.argv[1] if len(sys.argv) > 1 else 'output/results.json')
rows = json.loads(path.read_text(encoding='utf-8'))
print(json.dumps(validate_public_results(rows),indent=2))
