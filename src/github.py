"""Bounded public GitHub requests; only successfully retrieved evidence earns points."""
import datetime as dt
import json
import os
import re
import urllib.request
from urllib.error import HTTPError


class GitHubClient:
    def __init__(self, fetch=None, as_of=None, cache=None):
        self.fetch = fetch or self._fetch
        self.as_of = dt.date.fromisoformat(as_of) if as_of else dt.datetime.now(dt.timezone.utc).date()
        self.cache = cache if cache is not None else {}
        self.blocked = None

    def _fetch(self, url):
        headers = {'Accept':'application/vnd.github+json','User-Agent':'kasparro-screening-assignment'}
        token = os.getenv('GITHUB_TOKEN')
        if token:
            headers['Authorization'] = 'Bearer '+token
        request = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(request, timeout=8) as response:
            return json.load(response)

    def enrich(self, username):
        if not re.fullmatch(r'[A-Za-z0-9-]{1,39}',username):
            return dict(status='invalid_profile',points=0,merit=None,summary='Invalid GitHub username')
        key = username.lower() + ':' + self.as_of.isoformat()
        if key in self.cache:
            return self.cache[key]
        if self.blocked:
            result=dict(status='unavailable',points=0,merit=None,summary=self.blocked)
            self.cache[key]=result
            return result
        result = dict(status='unavailable',points=0,merit=None,summary='GitHub data unavailable',as_of=self.as_of.isoformat())
        try:
            base = 'https://api.github.com/users/'+username
            events = self.fetch(base+'/events/public?per_page=100')
            repos = self.fetch(base+'/repos?per_page=100&sort=pushed')
            if not isinstance(events,list) or not isinstance(repos,list):
                raise ValueError('Unexpected GitHub response shape')
            def recent(date, days):
                if not date:
                    return False
                age = (self.as_of-dt.date.fromisoformat(date[:10])).days
                return 0 <= age <= days
            engineering_events = [e for e in events if e.get('type') in ('PushEvent','PullRequestEvent','CreateEvent') and recent(e.get('created_at'),90)]
            maintained = [r for r in repos if not r.get('fork') and not r.get('archived') and recent(r.get('pushed_at'),180)]
            relevant = [r for r in maintained if r.get('language') == 'Python' or re.search(r'\brag\b|langchain|langgraph|machine learning|agent|llm',str(r.get('name',''))+' '+str(r.get('description','')),re.I)]
            activity = min(5,len(engineering_events))
            repository_points = min(5,len(maintained)+len(relevant))
            result.update(status='verified',points=activity+repository_points,merit='observed public signals only',
                          summary=f'{len(engineering_events)} recent engineering events; {len(maintained)} maintained repositories; {len(relevant)} relevant repositories.',
                          activity_points=activity,repository_points=repository_points,
                          evidence=dict(events=engineering_events,maintained_repos=maintained,relevant_repos=relevant),
                          sources=[base+'/events/public?per_page=100',base+'/repos?per_page=100&sort=pushed'],
                          fetched_at=dt.datetime.now(dt.timezone.utc).isoformat(),
                          limitation='First 100 public events/repos; public metadata is not proof of authorship or code quality.')
        except Exception as exc:
            result['summary'] = 'GitHub unavailable: '+type(exc).__name__
            if isinstance(exc, HTTPError):
                result['http_status'] = exc.code
                if exc.code in (401,403,429):
                    self.blocked = 'GitHub authentication/rate-limit circuit open; enrichment unavailable.'
        self.cache[key] = result
        return result
