"""Validate final files independently of the batch runner."""
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.config import WEIGHTS


def validate(output):
    rows=json.loads((output/'results.json').read_text(encoding='utf-8'))
    audit=json.loads((output/'audit.json').read_text(encoding='utf-8'))
    lookup={a['candidate_id']:a for a in audit}
    assert len(rows)==len(audit)==len(lookup)
    required={'rank','candidate_name','eligible','total_score','score_breakdown','matched_skills','project_summary','github_summary','strengths','concerns','evidence','rejection_reasons'}
    checked=0
    for row in rows:
        assert required<=row.keys()
        a=lookup[row['candidate_id']]
        for e in row['evidence']+row.get('penalties',[]):
            assert a['text'][e['start']:e['end']]==e['quote']
            checked+=1
        if row['eligible']:
            assert not row['rejection_reasons']
            assert set(row['score_breakdown'])==set(WEIGHTS)
            assert all(0<=row['score_breakdown'][k]<=v for k,v in WEIGHTS.items())
            assert row['total_score']==max(0,sum(row['score_breakdown'].values())-row['penalty_points'])
            for cat in WEIGHTS:
                if cat!='github':
                    assert row['score_breakdown'][cat]==sum(e['points'] for e in row['evidence'] if e['category']==cat)
            gh=row['github_enrichment']
            assert row['score_breakdown']['github']==gh['points']
            if gh['points']:
                assert gh['status']=='verified' and gh['evidence'] and gh['sources']
        else:
            assert row['rank'] is None and row['rejection_reasons']
    ranked=[r for r in rows if r['rank'] is not None]
    assert [r['rank'] for r in ranked]==list(range(1,len(ranked)+1))
    assert [r['total_score'] for r in ranked]==sorted((r['total_score'] for r in ranked),reverse=True)
    assert all(not r['duplicate_of'] and r['eligible'] for r in ranked)
    result=dict(status='passed',records=len(rows),evidence_spans_checked=checked,
                checks=['schema','category caps','arithmetic','evidence offsets','GitHub provenance','eligibility/rank consistency','sort order','duplicate exclusion'])
    (output/'validation.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    validate(Path(sys.argv[1] if len(sys.argv)>1 else 'output'))
