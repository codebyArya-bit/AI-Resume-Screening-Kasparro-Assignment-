"""Export required candidate results without direct identifiers or resume quotes."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.batch import public_results, write_json


parser = argparse.ArgumentParser()
parser.add_argument('input', type=Path, help='Private full results.json')
parser.add_argument('output', type=Path, nargs='?', default=Path('output/results.json'))
args = parser.parse_args()
rows = json.loads(args.input.read_text(encoding='utf-8'))
write_json(args.output, public_results(rows))
print(f'Exported {len(rows)} privacy-safe candidate rows to {args.output}')
