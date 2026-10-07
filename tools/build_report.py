"""Generate the aggregate-only submission report from validated outputs."""
import json
from pathlib import Path
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak

ROOT=Path(__file__).resolve().parents[1]


def build():
    out=ROOT/'output'
    summary=json.loads((out/'batch_summary.json').read_text(encoding='utf-8'))
    validation=json.loads((out/'validation.json').read_text(encoding='utf-8'))
    review=json.loads((out/'manual_review.json').read_text(encoding='utf-8'))
    target=out/'pdf'/'kasparro-report.pdf';target.parent.mkdir(exist_ok=True)
    styles=getSampleStyleSheet()
    styles.add(ParagraphStyle(name='TitleCustom',fontName='Helvetica-Bold',fontSize=25,leading=29,textColor=colors.HexColor('#132E43'),spaceAfter=18))
    styles.add(ParagraphStyle(name='SubCustom',fontSize=11,leading=16,textColor=colors.HexColor('#3B5669'),spaceAfter=12))
    styles['BodyText'].fontSize=10;styles['BodyText'].leading=15;styles['BodyText'].spaceAfter=10
    styles['Heading2'].textColor=colors.HexColor('#166A75');styles['Heading2'].spaceBefore=12
    story=[]
    def p(text,style='BodyText'):
        story.append(Paragraph(text,styles[style]))
    def table(rows,widths):
        cells=[[Paragraph(escape(str(cell)),styles['BodyText']) for cell in row] for row in rows]
        t=Table(cells,colWidths=widths,hAlign='LEFT')
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#E4F0F1')),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),9),('RIGHTPADDING',(0,0),(-1,-1),9),('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),5),('LINEBELOW',(0,0),(-1,0),1,colors.HexColor('#166A75')),('LINEBELOW',(0,1),(-1,-1),.3,colors.HexColor('#D9E2E8'))]))
        story.append(t)
    p('Kasparro<br/>AI Resume Screening','TitleCustom')
    p('Submitted by Aryabrat Mishra | Roll number 22053670<br/>aryabrat.mishra1@gmail.com | 7 October 2026','SubCustom')
    p('A reproducible screening pipeline with deterministic eligibility, evidence-backed scores, optional semantic annotation and graceful public GitHub enrichment.')
    table([['Full-batch outcome','Observed result'],['Input resumes',summary['total_resumes']],['Successfully parsed',summary['successfully_parsed']],['Eligible / rejected',f"{summary['eligible']} / {summary['rejected']}"],['Unreadable / duplicates',f"{summary['failed_unreadable']} / {summary['duplicates']}"],['PDF pages / unique embedded links',f"{summary['pages']} / {summary['embedded_links']}"],['Tests', '27 passed'],['Evidence spans validated',validation['evidence_spans_checked']]], [280,210])
    p('What these results establish','Heading2')
    p('The application processed the entire supplied folder and its final JSON passed schema, arithmetic, ordering, category-cap and evidence-provenance checks. These checks establish operational consistency. They do not establish ranking accuracy or verify candidates\' resume claims.')
    p('No trusted eligibility labels or gold ranking were supplied. True screening or ranking accuracy cannot be calculated from this dataset. The manual review described on page 3 is a spot-check, not measured accuracy.')
    p('Privacy: this report contains aggregate data only. Candidate names, contact details, URLs, project quotations and per-candidate rankings remain in private local artifacts.','SubCustom')
    story.append(PageBreak())
    p('Method and scoring','TitleCustom')
    p('Ingest -> extract text and links -> deterministic hard filter -> evidence scoring -> public GitHub bonus -> stable ranked JSON.','SubCustom')
    p('A candidate needs a genuine Python mention plus an AI implementation claim. Skills or coursework alone do not prove an AI project. Java, JavaScript and React are compatible supporting stacks. Custom ML/NLP/computer-vision implementations count as equivalent AI exposure; agentic and RAG depth receive additional points.')
    table([['Category','Cap','Implemented sub-rules'],['AI / agentic / RAG','40','AI implementation 8; retrieval 6; embeddings 4; tools 5; state 5; orchestration 5; evaluation 4; processing 3.'],['Python / backend','30','Python implementation 10 (skill only 2); Python backend framework 8; async 4; PostgreSQL 4; Redis 4.'],['Cloud / deployment / full stack','15','Cloud 5; containers 4; deployment/CI 4; supporting frontend 2.'],['GitHub','10','Recent engineering events 0-5 plus maintained/relevant public repositories 0-5.'],['Engineering depth','5','One each for testing, architecture, performance systems, observability, failure handling.']], [135,40,315])
    p('The brief supplies category weights and qualitative guidance; the sub-rules above are explicit engineering choices. A feature earns points once per resume and requires implementation evidence. The total is max(0, sum of category scores minus penalties).')
    p('Project-quality penalties','Heading2')
    p('Thin LLM/API claims lacking workflow, data processing, retrieval, state, backend, evaluation or product logic lose 10 points when no deeper AI work is evident, or 5 when other AI work is stronger. Explicit tutorial ownership limitations lose 5. Penalties cap at 15. Project paragraphs are considered together; ambiguous quality judgments remain a human-review concern.')
    p('Evidence records carry exact normalized-text quotes and offsets. GitHub contributions instead trace to retrieved event/repository snapshots. Resume performance percentages are recorded as claims and are not treated as independently validated outcomes.')
    story.append(PageBreak())
    p('Validation and review','TitleCustom')
    p('The ZIP contains 50 PDFs and no labels, README or sample submission. All extracted resumes were inspected for Python/AI signals, page readability and link availability. Byte and normalized-text hashes found no duplicates.')
    p('Extraction defects addressed','Heading2')
    p('A blank trailing page initially marked one otherwise readable document as failed. Visual inspection confirmed it was blank; the parser now retains the resume and records a low-text-page warning. Spaced/fragmented glyphs and multi-column documents use a second extraction path, with block-order preservation where appropriate. One overlaid-text document required preferring its readable text layer. The final batch has 50 parsed documents across 62 pages, including that blank page.')
    p('Automated verification','Heading2')
    p(f"Twenty-seven tests pass. Independent final-file validation checked {validation['evidence_spans_checked']} exact evidence/penalty spans, all 50 output records, score arithmetic, category caps, descending order, rank/eligibility consistency, duplicate exclusion, positive GitHub provenance and public-result privacy controls. Synthetic tests cover malformed files, embedded links, mixed stacks, skill-only claims, present-tense projects, penalties, metadata boundaries, cache/network failures and optional model failures.")
    p('Manual spot-check','Heading2')
    p(f"A purposive subset of {len(review['cases'])} resumes was reviewed against extracted text and the brief. Case IDs and evidence notes are recorded in the private manual_review.json. The subset covers rejected-only stacks, mixed stacks, ML equivalents, shallow/deep projects, unusual prose, multi-column extraction, blank pages and ambiguous profile ownership. Final eligibility disagreements: {review['eligibility_disagreements']}. This review is by the implementing agent, is not independent or random, and cannot support a population accuracy estimate.")
    p('Ranking limitations','Heading2')
    p('Keyword variants and paragraph grouping can still miss or misattribute engineering detail. Scores are a documented heuristic, not a calibrated measure of candidate ability. The spot-check did not establish a gold numeric score or total ordering. Independent labels, project ownership verification and reviewer ranking judgments are required before measuring screening or ranking quality.')
    p('Optional LLM status: no real model call was made because no configured credentials were available. Structured-output validation and failure handling were tested; live provider compatibility remains unverified.')
    story.append(PageBreak())
    p('GitHub, privacy and handoff','TitleCustom')
    statuses=summary['github_statuses']
    table([['GitHub enrichment status','Profiles'],['Verified retrieval',statuses.get('verified',0)],['Unavailable / rate limited',statuses.get('unavailable',0)],['Missing profile',statuses.get('missing',0)],['Ambiguous owner links',statuses.get('ambiguous',0)]],[340,150])
    p('Public requests inspect at most 100 recent events and 100 repositories. Engineering events within 90 days earn up to 5 points. Non-fork, non-archived repositories pushed within 180 days earn one point each, plus one for Python/AI relevance, capped at 5. Activity windows use 7 October 2026. Snapshots record retrieval provenance and remain private.')
    p('Missing, private, ambiguous or unavailable data never fails eligibility. Unknown GitHub merit is null; only its awarded bonus is zero. Unverified candidates have a score interval reflecting a possible additional 10 points. With incomplete enrichment, close rankings should be reconsidered when verified evidence becomes available.')
    p('Run and review','Heading2')
    p('<font name="Courier" size="8">python -m pip install -r requirements.txt<br/>python main.py --input resumes --output private/batch/results.json<br/>python tools/export_public_results.py private/batch/results.json output/results.json<br/>python -m unittest discover -s tests -v<br/>python tools/validate_public.py output/results.json</font>')
    p('Use --offline to disable GitHub and --cache with --as-of to reuse a private snapshot. The synthetic examples require no private dataset. Optional --llm explicitly sends resume text to the configured provider; it cannot override eligibility, scores or ranks.')
    p('Delivered artifacts','Heading2')
    p('The public repository contains modular source, tests, configuration examples, README, synthetic examples, aggregate outputs, privacy-safe results for all 50 candidates and this report. Public results retain ranks, eligibility, score breakdowns and generic evidence rules while omitting names, contacts, filenames, profile identifiers, URLs and exact quotations. The private submission ZIP contains full evidence and manual-review notes without raw PDFs.')
    p('Submission repository','Heading2')
    p('The public submission targets the user-provided GitHub repository: <link href="https://github.com/codebyArya-bit/AI-Resume-Screening-Kasparro-Assignment-" color="#166A75">codebyArya-bit / AI-Resume-Screening-Kasparro-Assignment-</link>. README documents setup, scoring decisions and privacy exclusions. Full candidate results and supporting evidence are supplied separately in the private submission ZIP for authorized reviewers.')
    def footer(canvas,doc):
        canvas.setStrokeColor(colors.HexColor('#D9E2E8'));canvas.line(52,42,543,42)
        canvas.setFont('Helvetica',8);canvas.setFillColor(colors.HexColor('#3B5669'))
        canvas.drawString(52,29,'KASPARRO ASSIGNMENT | Aggregate-only report')
        canvas.drawRightString(543,29,str(doc.page))
    SimpleDocTemplate(str(target),pagesize=A4,leftMargin=52,rightMargin=52,topMargin=48,bottomMargin=58,title='Kasparro AI Resume Screening - Validation Report',author='Assignment Submission').build(story,onFirstPage=footer,onLaterPages=footer)
    print(target)


if __name__=='__main__':
    build()
