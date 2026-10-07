import argparse
import json
from pathlib import Path
from src.batch import run, write_json, public_summary


def main():
    parser = argparse.ArgumentParser(description='Evidence-backed resume screening; results require human review.')
    parser.add_argument('--input',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--offline',action='store_true',help='Disable GitHub requests')
    parser.add_argument('--llm',action='store_true',help='Opt in to sending resume text to configured model provider')
    parser.add_argument('--as-of',help='YYYY-MM-DD for recent activity windows')
    parser.add_argument('--cache',type=Path,help='Private snapshot cache; reuse only for a reproducible run')
    args = parser.parse_args()
    if not args.input.is_dir():
        parser.error('Input must be a directory')
    cache = json.loads(args.cache.read_text(encoding='utf-8')) if args.cache and args.cache.exists() else {}
    rows,summary,audit = run(args.input,github=not args.offline,llm=args.llm,as_of=args.as_of,cache=cache)
    write_json(args.output,rows)
    write_json(args.output.parent/'audit.json',audit)
    write_json(args.output.parent/'batch_summary.json',public_summary(summary,rows))
    if args.cache:
        write_json(args.cache,cache)
    print(json.dumps(summary,indent=2))
    if summary['failed_unreadable']:
        print('WARNING: Failed files are retained for manual review; inspect audit.json.')


if __name__ == '__main__':
    main()
