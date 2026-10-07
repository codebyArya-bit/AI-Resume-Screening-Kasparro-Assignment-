import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class ScreeningTests(unittest.TestCase):
    def screen(self, text):
        self.assertIsNotNone(importlib.util.find_spec('src.scoring'), 'Screening module must exist')
        from src.scoring import screen
        return screen(text)

    def test_mixed_stack_is_eligible(self):
        r = self.screen('Skills: Python, Java, React\nProjects\nBuilt a RAG assistant using LangChain with semantic retrieval and session memory.')
        self.assertTrue(r['eligible'])

    def test_skills_and_coursework_alone_do_not_prove_ai(self):
        r = self.screen('Skills: Python, LangChain, RAG, AI\nEducation\nCoursework: Artificial Intelligence\nBuilt a React shopping cart.')
        self.assertFalse(r['eligible'])

    def test_ai_without_python_rejected(self):
        r = self.screen('Built a LangGraph multi-agent workflow with state and retrieval using TypeScript.')
        self.assertFalse(r['eligible'])
        self.assertIn('No evidence of Python stack', r['rejection_reasons'])

    def test_unusual_heading_and_custom_ml(self):
        r = self.screen('Languages: Python\nSelected work\nTrained a CNN on images with preprocessing and evaluation.')
        self.assertTrue(r['eligible'])

    def test_non_ai_agent_and_ai_coding_tools_rejected(self):
        self.assertFalse(self.screen('Python developer. Built a real estate agent portal using React. Used GitHub Copilot for coding.')['eligible'])

    def test_python_negation_not_a_skill(self):
        self.assertFalse(self.screen('No Python experience. Built a RAG assistant with vector retrieval.')['eligible'])

    def test_ai_wrapper_penalty_and_depth_order(self):
        thin = self.screen('Skills: Python\nProjects\nBuilt a chatbot using Gemini API to answer prompts.')
        deep = self.screen('Python\nProjects\nBuilt a RAG agent using LangGraph with embeddings, retrieval, tool calling, state, orchestration, evaluation and data processing.\nImplemented async FastAPI with PostgreSQL and Redis caching, tests, Docker deployment on GCP.')
        self.assertTrue(thin['eligible'])
        self.assertGreaterEqual(thin['penalty_points'], 5)
        self.assertGreater(deep['total_score'], thin['total_score'])
        self.assertEqual(deep['total_score'], sum(deep['score_breakdown'].values()) - deep['penalty_points'])

    def test_skill_lists_cannot_fill_category_caps(self):
        r = self.screen('Skills: Python, FastAPI, Redis, PostgreSQL, Docker, GCP, LangGraph, testing\nProjects\nBuilt a chatbot using OpenAI API.')
        self.assertLess(r['score_breakdown']['python_backend'], 30)
        self.assertLess(r['score_breakdown']['cloud_fullstack'], 15)
        self.assertLess(r['score_breakdown']['ai_project_depth'], 40)

    def test_evidence_is_locatable(self):
        text = 'Skills: Python\nBuilt a RAG pipeline with embeddings and retrieval.'
        r = self.screen(text)
        for evidence in r['evidence']:
            self.assertEqual(text[evidence['start']:evidence['end']], evidence['quote'])

    def test_present_tense_implementation(self):
        r = self.screen('Skills\nPython, Flask\nProjects\nElectric Vehicle Knowledge Bot\nIt uses a Flask backend with a chatbot API.\nThe system leverages LLM/RAG techniques with SQLite for data handling and retrieval.')
        self.assertTrue(r['eligible'])

    def test_followup_ai_details_and_unrelated_project_boundary(self):
        r = self.screen('Skills\nPython\nProjects\nRAG Assistant | Python\nBuilt a RAG pipeline with LangGraph.\nImplemented tool calling and checkpointed shared state.\nDesigned an evaluation pipeline with chunking.\nShopping Cart | React\nImplemented vector embeddings as a skill demonstration.')
        self.assertGreaterEqual(r['score_breakdown']['ai_project_depth'], 30)
        self.assertFalse(any(e['rule']=='embeddings' for e in r['evidence']))

    def test_summary_claims_and_skill_metadata_do_not_earn_depth(self):
        r = self.screen('Summary\nExperienced in building LangGraph RAG agents with state, retrieval and tools.\nSkills\nPython, FastAPI, PostgreSQL, Redis\nProjects\nBuilt a chatbot using Gemini API.')
        self.assertEqual(r['score_breakdown']['ai_project_depth'], 8)
        self.assertEqual(r['score_breakdown']['python_backend'], 2)

    def test_word_experience_in_summary_does_not_start_work_section(self):
        r = self.screen('Summary\nFull-stack engineer with experience building production RAG pipelines with retrieval.\nSkills\nPython\nProjects\nBuilt a chatbot using Gemini API.')
        self.assertEqual(r['score_breakdown']['ai_project_depth'],8)

    def test_complete_project_avoids_thin_wrapper_penalty(self):
        r = self.screen('Skills\nPython\nProjects\nResearch Copilot\nBuilt an assistant using LangGraph and LLM APIs.\nDesigned shared state and conditional routing with session persistence.')
        self.assertEqual(r['penalty_points'],0)

    def test_glued_action_and_project_technology_evidence(self):
        from src.ingest import normalize
        r = self.screen(normalize('Skills\nPython\nProjects\nReview Intelligence | Python, Flask, NLP\nDeployedmultimodal models with speech recognition and contextual orchestration.'))
        self.assertTrue(r['eligible'])
        self.assertGreaterEqual(r['score_breakdown']['python_backend'],10)

    def test_ml_prediction_and_log_analysis(self):
        r = self.screen('Skills\nPython\nProjects\nDesigned a serverless ML prediction system using Scikit-learn.\nIntegrated an OpenAI log analyser that diagnoses failures.')
        self.assertTrue(r['eligible'])

    def test_structured_backend_business_logic_is_not_thin_wrapper(self):
        r = self.screen('Python\nProjects\nDesigned an AI-driven CRM system converting natural language to structured data using LangGraph, Groq LLM, FastAPI and React.')
        self.assertEqual(r['penalty_points'],0)

    def test_model_timeout_keeps_deterministic_result(self):
        from src.llm import annotate
        text='Python\nBuilt a RAG assistant with retrieval.'
        with patch.dict('os.environ',{'LLM_API_KEY':'synthetic-test-key','LLM_MODEL':'synthetic-model'}):
            with patch('urllib.request.urlopen',side_effect=TimeoutError):
                self.assertEqual(annotate(text)['status'],'unavailable')
        self.assertTrue(self.screen(text)['eligible'])


class IntegrationTests(unittest.TestCase):
    def module(self, name):
        self.assertIsNotNone(importlib.util.find_spec(name), name + ' must exist')
        return __import__(name, fromlist=['*'])

    def test_embedded_github_and_broken_pdf(self):
        ingest = self.module('src.ingest')
        from reportlab.pdfgen.canvas import Canvas
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'a.pdf'
            c = Canvas(str(p)); c.drawString(50, 700, 'GitHub')
            c.linkURL('https://github.com/example-user/rag-demo', (50, 690, 100, 710)); c.save()
            r = ingest.extract(p)
            self.assertIn('https://github.com/example-user/rag-demo', r['links'])
            self.assertEqual(ingest.github_profiles(r['text'], r['links']), ['example-user'])
            p.write_bytes(b'not a PDF')
            self.assertEqual(ingest.extract(p)['status'], 'failed')

    def test_batch_duplicates_failures_and_sort(self):
        batch = self.module('src.batch')
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            txt = 'Python\nBuilt a RAG pipeline with embeddings and retrieval.'
            (folder/'a.txt').write_text(txt); (folder/'b.txt').write_text(txt)
            (folder/'bad.pdf').write_bytes(b'broken')
            (folder/'empty.txt').write_text('')
            rows, summary, audit = batch.run(folder, github=False)
            self.assertEqual(len(rows), 4)
            self.assertEqual(summary['duplicates'], 1)
            self.assertEqual(summary['failed_unreadable'], 2)
            self.assertEqual(sum(r['rank'] is not None for r in rows), 1)

    def test_blank_trailing_page_retains_readable_resume(self):
        ingest = self.module('src.ingest')
        from reportlab.pdfgen.canvas import Canvas
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/'blank.pdf'
            c = Canvas(str(p));c.drawString(40,700,'Python developer built a RAG assistant with retrieval.')
            c.showPage();c.showPage();c.save()
            r = ingest.extract(p)
            self.assertEqual(r['status'],'parsed')
            self.assertEqual(len(r['pages']),2)
            self.assertTrue(r['warnings'])

    def test_github_verified_scores_and_cache(self):
        gh = self.module('src.github')
        calls = []
        def fetch(url):
            calls.append(url)
            if '/events' in url:
                return [{'type':'PushEvent','created_at':'2026-10-01T00:00:00Z'}]
            return [{'name':'rag-demo','language':'Python','description':'RAG','fork':False,'archived':False,'pushed_at':'2026-10-01T00:00:00Z'}]
        client = gh.GitHubClient(fetch=fetch, as_of='2026-10-07')
        r = client.enrich('example-user')
        self.assertEqual(r['status'], 'verified')
        self.assertGreater(r['points'], 0)
        self.assertLessEqual(r['points'], 10)
        client.enrich('example-user')
        self.assertEqual(len(calls), 2)

    def test_github_failure_is_unknown(self):
        gh = self.module('src.github')
        def fetch(url):
            raise TimeoutError('network')
        r = gh.GitHubClient(fetch=fetch).enrich('example-user')
        self.assertEqual(r['status'], 'unavailable')
        self.assertIsNone(r['merit'])
        self.assertEqual(r['points'], 0)

    def test_llm_invalid_or_invented_evidence_fails_gracefully(self):
        llm = self.module('src.llm')
        self.assertEqual(llm.validate_annotation({'project_summary':'x','evidence':['invented']}, 'Python')['status'], 'invalid')
        self.assertEqual(llm.validate_annotation({'project_summary':'x','evidence':['Python']}, 'Python')['status'], 'verified')

    def test_public_export_keeps_required_fields_and_removes_identifiers(self):
        batch = self.module('src.batch')
        private = [{
            'candidate_id':'candidate_001', 'candidate_name':'Asha Rao', 'rank':1,
            'parse_status':'parsed', 'duplicate_of':None, 'eligible':True,
            'rejection_reasons':[], 'matched_skills':['Python','RAG'],
            'score_breakdown':{'ai_project_depth':20,'python_backend':10,'cloud_fullstack':0,'github':0,'engineering_depth':0},
            'penalties':[{'rule':'thin_wrapper','points':5,'quote':'Built at Secret College'}],
            'penalty_points':5, 'total_score':25,
            'evidence':[{'category':'ai_project_depth','rule':'retrieval','points':6,'quote':'Secret project for Acme','start':10,'end':33}],
            'project_summary':'Secret project for Acme', 'strengths':['Secret College winner'],
            'concerns':['Contact asha@example.com'],
            'github_profile_candidates':['asha-private'],
            'github_enrichment':{'status':'verified','summary':'1 recent engineering event; 1 maintained repositories; 1 relevant repositories.','sources':['https://github.com/asha-private']},
            'github_summary':'1 recent engineering event; 1 maintained repositories; 1 relevant repositories.',
            'score_interval':[25,25], 'llm_annotation':{'status':'disabled'},
            'shortlist_eligible':True,
        }]
        with patch('secrets.token_hex', return_value='a1b2c3d4'):
            public = batch.public_results(private)
        self.assertEqual(public[0]['candidate_id'], 'applicant_a1b2c3d4')
        self.assertEqual(public[0]['rank'], 1)
        self.assertEqual(public[0]['score_breakdown']['ai_project_depth'], 20)
        self.assertEqual(public[0]['evidence'], [{'category':'ai_project_depth','rule':'retrieval','points':6}])
        exported = json.dumps(public)
        for secret in ('Asha Rao','candidate_001','Secret','Acme','asha@example.com','asha-private','github.com'):
            self.assertNotIn(secret, exported)

    def test_public_export_assigns_unique_ids(self):
        batch = self.module('src.batch')
        rows = [dict(rank=1), dict(rank=2)]
        with patch('secrets.token_hex', side_effect=['11111111','11111111','22222222']):
            public = batch.public_results(rows)
        self.assertEqual([r['candidate_id'] for r in public], ['applicant_11111111','applicant_22222222'])

    def test_public_validation_rejects_identifier_fields(self):
        batch = self.module('src.batch')
        with patch('secrets.token_hex', return_value='a1b2c3d4'):
            public = batch.public_results([{'rank':None,'eligible':False,'rejection_reasons':['No Python evidence']}])
        self.assertEqual(batch.validate_public_results(public)['records'], 1)
        public[0]['candidate_name'] = 'Private Name'
        with self.assertRaises(AssertionError):
            batch.validate_public_results(public)


if __name__ == '__main__':
    unittest.main()
