"""One result per input; duplicates are preserved but not shortlisted twice."""
import collections
import hashlib
import json
import re
import secrets
from pathlib import Path
from .ingest import extract, github_profiles
from .scoring import screen
from .github import GitHubClient
from .llm import annotate


def run(folder, github=True, llm=False, as_of=None, cache=None):
    folder = Path(folder)
    files = sorted(p for p in folder.rglob('*') if p.is_file())
    if not files:
        raise ValueError('No input files found')
    client = GitHubClient(as_of=as_of,cache=cache)
    rows, audit, hashes, texts = [], [], {}, {}
    for index,path in enumerate(files,1):
        data = extract(path)
        candidate_id = f'candidate_{index:03d}'
        duplicate = hashes.get(data['sha256']) or texts.get(data['text_sha256'])
        if data['sha256']:
            hashes.setdefault(data['sha256'],candidate_id)
        if data['text_sha256']:
            texts.setdefault(data['text_sha256'],candidate_id)
        row = dict(candidate_id=candidate_id,candidate_name=candidate_id,rank=None,
                   parse_status=data['status'],duplicate_of=duplicate)
        if data['status'] == 'parsed':
            row.update(screen(data['text']))
            profiles = github_profiles(data['text'],data['links'])
            enrichment = dict(status='missing',points=0,merit=None,summary='No GitHub profile found')
            if len(profiles) > 1:
                # Do not attribute an arbitrary linked repository owner to the candidate.
                enrichment = dict(status='ambiguous',points=0,merit=None,summary='Multiple GitHub owners found; manual identity verification required')
            elif profiles:
                enrichment = client.enrich(profiles[0]) if github else dict(status='unverified',points=0,merit=None,summary='GitHub enrichment disabled')
            row['github_profile_candidates'] = profiles
            row['github_enrichment'] = enrichment
            row['github_summary'] = enrichment['summary']
            if row['eligible']:
                row['score_breakdown']['github'] = enrichment['points']
                row['total_score'] = max(0,sum(row['score_breakdown'].values())-row['penalty_points'])
                row['score_interval'] = [row['total_score'],min(100,row['total_score']+10)] if enrichment['merit'] is None else [row['total_score']]*2
                if enrichment['merit'] is None:
                    row['concerns'].append('GitHub merit unknown; awarded contribution is zero, not evidence of zero merit.')
            if llm:
                row['llm_annotation'] = annotate(data['text'])
            else:
                row['llm_annotation'] = {'status':'disabled'}
        else:
            row.update(eligible=False,rejection_reasons=['Unreadable; manual review required'],
                       total_score=None,score_breakdown=None,matched_skills=[],evidence=[],
                       project_summary='Unavailable',github_summary='Not attempted',strengths=[],concerns=['Extraction failed'])
        row['shortlist_eligible'] = row['eligible'] and not duplicate
        if duplicate:
            row['concerns'].append('Duplicate input; retained for audit and omitted from shortlist.')
        rows.append(row)
        audit.append(dict(candidate_id=candidate_id,source_relative_path=str(path.relative_to(folder)),
                          extracted_contact=dict(emails=sorted(set(re.findall(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}',data['text']))),
                                                 name_guess=data['text'].splitlines()[0] if data['text'] else None,
                                                 name_status='unverified first-line heuristic; output uses pseudonym'),
                          **{k:data.get(k) for k in ('status','sha256','text_sha256','pages','text','links','warnings','error','extraction_method')}))
    shortlist = sorted((r for r in rows if r['shortlist_eligible']),key=lambda r:(-r['total_score'],r['candidate_id']))
    for rank,row in enumerate(shortlist,1):
        row['rank'] = rank
    rows.sort(key=lambda r:(r['rank'] is None,r['rank'] or 0,r['candidate_id']))
    parsed = sum(r['parse_status']=='parsed' for r in rows)
    eligible = sum(r['eligible'] for r in rows)
    summary = dict(total_resumes=len(rows),successfully_parsed=parsed,eligible=eligible,
                   rejected=sum(r['parse_status']=='parsed' and not r['eligible'] for r in rows),
                   failed_unreadable=len(rows)-parsed,duplicates=sum(bool(r['duplicate_of']) for r in rows),
                   shortlisted=len(shortlist),pages=sum(len(a['pages']) for a in audit),
                   embedded_links=sum(len(a['links']) for a in audit),
                   github_statuses=dict(collections.Counter(r.get('github_enrichment',{}).get('status','not_attempted') for r in rows)),
                   llm_enabled=llm,ranking_accuracy=None,
                   accuracy_note='No trusted eligibility labels or gold ranking supplied. Parsing success is not accuracy.')
    return rows, summary, audit


def public_summary(summary, rows):
    scores = [r['total_score'] for r in rows if r.get('shortlist_eligible')]
    return dict(summary,score_distribution=dict(count=len(scores),minimum=min(scores) if scores else None,
                                                maximum=max(scores) if scores else None,
                                                mean=round(sum(scores)/len(scores),2) if scores else None),
                privacy='Public candidate results use random IDs and omit names, contacts, filenames, profile identifiers, URLs and evidence quotations.')


def public_results(rows):
    """Return assignment-complete candidate rows without direct identifiers or quotes."""
    public, used_ids = [], set()
    for row in rows:
        while True:
            public_id = 'applicant_' + secrets.token_hex(4)
            if public_id not in used_ids:
                used_ids.add(public_id)
                break
        evidence = [
            {key: item[key] for key in ('category','rule','points') if key in item}
            for item in row.get('evidence',[])
        ]
        penalties = [
            {key: item[key] for key in ('rule','points') if key in item}
            for item in row.get('penalties',[])
        ]
        evidence_rules = sorted({item.get('rule','').replace('_',' ') for item in evidence if item.get('rule')})
        status = row.get('github_enrichment',{}).get('status','not_attempted')
        github_points = (row.get('score_breakdown') or {}).get('github',0)
        public.append({
            'candidate_id':public_id,
            'rank':row.get('rank'),
            'parse_status':row.get('parse_status'),
            'eligible':row.get('eligible'),
            'rejection_reasons':row.get('rejection_reasons',[]),
            'matched_skills':row.get('matched_skills',[]),
            'score_breakdown':row.get('score_breakdown'),
            'penalties':penalties,
            'penalty_points':row.get('penalty_points',0),
            'total_score':row.get('total_score'),
            'evidence':evidence,
            'project_summary':('Evidence recorded for: ' + ', '.join(evidence_rules) + '.') if evidence_rules else 'No scored project evidence.',
            'github_status':status,
            'github_summary':f'{status.replace("_"," ").title()}; awarded {github_points}/10 GitHub points.',
            'score_interval':row.get('score_interval'),
            'shortlist_eligible':row.get('shortlist_eligible',False),
            'is_duplicate':bool(row.get('duplicate_of')),
        })
    return public


def validate_public_results(rows):
    required = {'candidate_id','rank','parse_status','eligible','rejection_reasons','matched_skills',
                'score_breakdown','penalty_points','total_score','evidence','project_summary',
                'github_status','github_summary','score_interval','shortlist_eligible','is_duplicate'}
    forbidden = {'candidate_name','duplicate_of','github_profile_candidates','github_enrichment',
                 'llm_annotation','quote','start','end','sources'}
    def keys(value):
        if isinstance(value,dict):
            return set(value).union(*(keys(item) for item in value.values()))
        if isinstance(value,list):
            return set().union(*(keys(item) for item in value)) if value else set()
        return set()
    assert rows and len({row['candidate_id'] for row in rows}) == len(rows)
    assert all(re.fullmatch(r'applicant_[0-9a-f]{8}',row['candidate_id']) for row in rows)
    assert all(required <= row.keys() for row in rows)
    assert not forbidden.intersection(keys(rows))
    for row in rows:
        if row['eligible']:
            assert row['total_score'] == max(0,sum(row['score_breakdown'].values())-row['penalty_points'])
        else:
            assert row['rank'] is None and row['rejection_reasons']
    ranked = [row for row in rows if row['rank'] is not None]
    assert [row['rank'] for row in ranked] == list(range(1,len(ranked)+1))
    assert [row['total_score'] for row in ranked] == sorted((row['total_score'] for row in ranked),reverse=True)
    return {'status':'passed','records':len(rows),'ranked':len(ranked),
            'privacy':'direct identifiers, URLs and evidence quotes absent'}


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
