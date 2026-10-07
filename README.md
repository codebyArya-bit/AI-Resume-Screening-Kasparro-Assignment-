# Kasparro AI Resume Screening

**Submitted by:** Aryabrat Mishra  
**Roll number:** 22053670  
**Email:** aryabrat.mishra1@gmail.com

A small Python CLI that parses a folder, applies the assignment's Python + AI hard filter, scores eligible candidates out of 100, and records evidence for every awarded point. Results support human review; they are not validated hiring decisions.

## Setup and run

Python 3.10+ is required. Run from this directory:

```sh
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py --input ./resumes --output ./private/batch/results.json
python tools/export_public_results.py private/batch/results.json output/results.json
python -m unittest discover -s tests -v
python tools/validate_batch.py private/batch
python tools/validate_public.py output/results.json
```

No API key is required. The default run makes bounded, sequential requests to the public GitHub API. Set `GITHUB_TOKEN` in your environment to improve the rate limit. `.env.example` documents optional variables; environment files are not loaded automatically.

```sh
# Offline demonstration uses explicitly synthetic resumes.
python main.py --input examples/resumes --output private/demo/results.json --offline
# Fixed-date run with private snapshot cache:
python main.py --input private/resumes --output private/batch/results.json --as-of 2026-10-07 --cache private/batch/github_cache.json
python tools/export_public_results.py private/batch/results.json output/results.json
# Optional semantic annotation; explicit opt-in sends resume text to a provider:
python main.py --input resumes --output output/results.json --llm
```

The LLM adapter accepts an HTTPS, OpenAI-compatible chat-completions endpoint configured by `LLM_BASE_URL`, `LLM_MODEL`, and `LLM_API_KEY`. Provider support for strict JSON schema is required. A failure returns an unavailable annotation and retains deterministic results. The live LLM path was not exercised with real credentials; schema validation and timeout handling were tested.

## Outputs and privacy

Private `results.json` contains complete evidence for authorized review. Public `output/results.json` contains all 50 candidates with random applicant IDs, ranks, eligibility, rejection reasons, matched skills, score breakdowns, generic evidence rules, project summaries and GitHub status. It omits names, emails, filenames, profile identifiers, URLs and exact resume quotations.

Every resume score evidence record has an exact quote plus start/end offsets into the normalized text in `audit.json`. Those offsets are **text positions, not PDF coordinates**. GitHub points trace to separate retrieved public events/repository snapshots and source URLs. Penalties are separate from the five category scores: `total_score = max(0, sum(score_breakdown) - penalty_points)`.

`batch_summary.json`, `validation.json`, `privacy_check.json` and privacy-safe `results.json` are public exports. Full results, `audit.json`, `manual_review.json`, caches and all dataset files remain private and Git-ignored. Pseudonyms alone do not anonymize unique project quotations or GitHub URLs, so public results exclude both. Private submission ZIP includes full results and audit evidence but no original PDFs. Share it only with authorized assignment reviewers.

## Design Decisions

**Filtering.** A genuine, non-negated Python mention and an implementation claim with AI technology/use-case evidence are both necessary. Mixed Java/React/Python profiles remain eligible. Skill lists, coursework and summaries do not establish AI implementation. Conventional ML, computer vision and NLP implementations count as equivalent AI exposure, consistent with the brief's broad AI requirement; agentic/RAG features earn more depth points. This is a documented interpretation, not a supplied eligibility label.

**Extraction.** PDF support uses pypdf and a geometric pdfplumber fallback for fragmented/spaced text. Embedded URI annotations are inspected independently of visible labels. TXT and DOCX support are included. Blank trailing pages produce warnings while retaining readable content. All-image documents fail to manual review; OCR is not implemented. Hashes detect byte-identical and normalized-text duplicates. Every input gets an audit record; duplicate candidates are not ranked twice. All files in the input folder are attempted, including unsupported formats, which are recorded as failures. Keep outputs outside the input folder.

**Scoring.** The assignment fixes category weights but supplies no exact per-feature formula. The implementation uses the following explicit deterministic sub-rules (`src/config.py`):

| Category | Cap | Award rules |
|---|---:|---|
| AI project depth | 40 | Implemented AI system 8; retrieval 6; embeddings 4; tools 5; state/memory 5; orchestration 5; evaluation 4; processing 3 |
| Python/backend | 30 | Python implementation or project technology 10 (skill-only 2); FastAPI/Flask/Django implementation 8; async 4; PostgreSQL 4; Redis 4 |
| Cloud/full stack | 15 | Cloud implementation 5; containers 4; deployment/CI 4; frontend 2 |
| GitHub | 10 | Up to 5 recent engineering events; up to 5 maintained/relevant repository signals |
| Engineering depth | 5 | One each for testing, architecture, caching/queues/concurrency, observability, failure handling |

Each sub-rule is awarded once per resume. Implementation evidence outranks keyword-only skill lists. Adjacent claims are grouped by conservative project/experience headings to capture details beyond the first AI sentence. Backend support signals can come from other languages; Python implementation has its own higher-value rule. Resume claims (including claimed accuracy percentages) are evidence of descriptions, not verified achievements.

**Penalties.** A thin LLM/API claim with no retrieval, state, workflow processing, backend/product logic or evaluation detail loses 10 points if no deeper AI evidence is found, or 5 when other AI work is stronger. Explicit tutorial-style ownership limitations lose 5. Combined penalties cap at 15. A project is assessed across its implementation paragraphs before applying a wrapper penalty. This remains a heuristic; ambiguous penalties warrant human review.

**GitHub.** Extract profile usernames from text and annotations. Multiple owners are marked ambiguous rather than attributed arbitrarily. Requests are limited to the first 100 public events and first 100 repositories sorted by pushed time. Count PushEvent, PullRequestEvent and CreateEvent within 90 days (0-5). Non-fork, non-archived repositories pushed within 180 days earn one point each, plus one for Python/AI relevance, capped at 5. This measures visible metadata, not verified code quality or authorship. Future-dated activity is excluded. HTTP auth/rate-limit errors open a circuit for the remaining batch. Per-profile cache avoids repeated calls. Snapshots are private; delete/replace the cache for a fresh evaluation.

Unavailable, missing or ambiguous GitHub merit is `null`. Its **awarded bonus** is zero; the candidate is not penalized or screened out. Eligible rows include a possible score interval with up to 10 unverified bonus points. These intervals are uncertainty bounds, not statistical confidence intervals. Rankings can change when missing evidence becomes available.

**LLM usage.** Optional semantic annotations use a strict JSON schema and verbatim evidence validation. Model outputs cannot modify hard filters, numeric scores or ranks. Deterministic scoring is the reproducible baseline. No credentials are hard-coded and no resume text is sent to an LLM without `--llm`.

## Validation

The supplied ZIP contains 50 PDFs and no README, sample submission, trusted labels or gold ranking. The DOCX brief and supplied SKILL.md were read; the skill concerns brainstorming process, not candidate scoring. The user's instruction to continue the already approved design took precedence over additional routine approval gates.

See `output/batch_summary.json`, `output/validation.json` and the PDF report for final measured counts. Automated checks independently verify output schema, category caps, arithmetic, ordering, ranks, duplicate exclusion, every exact evidence span and positive GitHub provenance. Twenty-seven unit/integration tests cover the hard filter, mixed skills, misleading skill claims, unusual headings, custom ML, project boundaries, penalties, malformed PDFs, embedded URLs, duplicates, blank pages, GitHub failures/cache, LLM invalid evidence/timeouts and privacy exports.

All 50 extracted resumes were inspected for Python/AI evidence and extraction problems. A documented manual spot-check of 15 selected cases covers rejected profiles, mixed stacks, unusual prose, ML equivalents, multi-column text, blank pages, ambiguous links and detailed agentic projects. This is a single agent's review, not independent gold labeling, a random sample, or measured accuracy. Candidate-level review notes stay private. No ranking accuracy percentage is asserted.

## Repository publication

Submission repository: [AI Resume Screening Kasparro Assignment](https://github.com/codebyArya-bit/AI-Resume-Screening-Kasparro-Assignment-).

The public submission contains code, dependencies, synthetic examples, tests, aggregate validation outputs, privacy-safe results for all 50 candidates and the PDF report. Full evidence is delivered separately in the private submission ZIP to authorized reviewers. Raw resumes, contact details, filenames, profile identifiers, URLs, unique evidence quotes and private caches must never be committed.

Review `git ls-files` before pushing. Never force-add ignored candidate outputs.

## If I Had More Time

1. Add OCR with confidence and page-level review queues, and stronger geometric section segmentation.
2. Obtain independent eligibility labels and pairwise ranking judgments, then measure screening precision/recall and ranking quality.
3. Validate project ownership/code quality and improve GitHub identity matching, pagination and recency normalization.
4. Evaluate semantic extraction against labeled projects while keeping eligibility deterministic and enforcing evidence constraints.
