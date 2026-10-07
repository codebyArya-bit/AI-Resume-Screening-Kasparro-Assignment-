"""Deterministic rules. Every awarded sub-score has an exact text span."""
import re
from .config import WEIGHTS, AI_FEATURES, BACKEND_FEATURES, CLOUD_FEATURES, ENGINEERING_FEATURES, SKILLS

ACTION = r'\b(?:built|build(?:ing)?|develop(?:ed|ing)?|implement(?:ed|ing)?|engineer(?:ed|ing)?|design(?:ed|ing)?|train(?:ed|ing)?|deploy(?:ed|ing)?|integrat(?:ed|ing|es)|architect(?:ed|ing)?|creat(?:ed|ing)|orchestrat(?:ed|ing)|optim(?:iz|is)(?:ed|ing)|fine.tun(?:ed|ing)|automat(?:ed|ing)|evaluat(?:ed|ing)|processed|preprocessed|enabled|wired|shipped|applied|enhanced|contributing|uses|leverages|predicts|performed|compared|instrumented|operationalised|hardened|exposed)\b'
AI = r'LangChain|LangGraph|LlamaIndex|\bRAG\b|retrieval.augmented|\bLLMs?\b|OpenAI|Gemini|GPT.?[2345]|\bBERT\b|\bNLP\b|machine learning|deep learning|\bCNNs?\b|convolutional|TensorFlow|PyTorch|Scikit.learn|transformer|semantic search|vector search|embeddings|CrewAI|AutoGen|Google ADK|agentic|multi.agent|tool.call|computer vision|YOLO|InsightFace|reinforcement learning|meta.heuristic|AI.powered|AI.driven'
DETAIL = r'pipeline|workflow|retriev|state|memory|model|classif|detect|predict|process|data|inference|chatbot|assistant|summari|agent|orchestrat|algorithm|generat|semantic|API|analy|diagnos|recommend|recognition'
META = r'^(?:technical skills|skills|core competencies|core technical expertise|education|certifications?|coursework|relevant coursework|professional summary|summary|objectives?|profile objective|ats keyword index|languages|programming languages)\b'
WORK = r'^(?:(?:(?:professional|work|internship|project|hackathon|research|key|selected)\s+)?(?:projects?|experience)|selected work|portfolio|research|publications|internships)\b'


def units(text):
    """Paragraph spans plus conservative project groups; metadata never earns depth."""
    boundaries = [(0,'unknown',0)]
    section, group = 'unknown',0
    for m in re.finditer(r'^.*$',text,re.M):
        line = m.group().strip()
        if not line:
            continue
        clean = re.sub(r'^[•●◆◦▪–-]\s*','',line)
        words = re.findall(r'[A-Za-z]+',clean)
        has_action = bool(re.search(ACTION,clean,re.I))
        meta = bool(re.search(META,clean,re.I)) and len(clean)<180
        work = bool(re.search(WORK,clean,re.I)) and len(clean)<180
        technology_line = bool(re.match(r'(?:Tools|Tech Stack|Technologies|Python\s*[,|]|T ools)',clean,re.I))
        title = (not has_action and not technology_line and len(clean)<180 and
                 ('|' in clean or (2<=len(words)<=12 and sum(w[0].isupper() for w in words)/len(words)>.7)))
        if meta:
            section='metadata';group+=1
        elif work:
            section='work';group+=1
        elif title and section!='metadata':
            group+=1
        bullet = bool(re.match(r'[•●◆◦▪–-]',line))
        action_start = bool(re.match(ACTION,clean,re.I))
        if meta or work or title or bullet or action_start:
            boundaries.append((m.start(),section,group))
    # Deduplicate the start-of-document boundary after classifying its first line.
    unique={a:(a,s,g) for a,s,g in boundaries}
    boundaries=sorted(unique.values())+[(len(text),section,group)]
    for (start,section,group),(end,_,_) in zip(boundaries,boundaries[1:]):
        raw=text[start:end];quote=raw.strip()
        if not quote:
            continue
        a=start+len(raw)-len(raw.lstrip());b=a+len(quote)
        yield dict(start=a,end=b,quote=quote,group=group,
                   implementation=section!='metadata' and bool(re.search(ACTION,quote,re.I)))


def screen(text):
    all_units=list(units(text))
    claims = [u for u in all_units if u['implementation']]
    group_context={}
    for u in all_units:
        group_context.setdefault(u['group'],[]).append(u)
    evidence = []

    def award(category, rule, points, match):
        evidence.append(dict(category=category, rule=rule, points=points,
                             start=match['start'], end=match['end'], quote=match['quote']))

    py = None
    for m in re.finditer(r'\bPython\b', text, re.I):
        context = text[max(0,m.start()-35):min(len(text),m.end()+35)]
        if re.search(r'no\s+Python|without\s+Python|not\s+(?:know|use).*Python|Python\s*:\s*(?:none|no)', context, re.I):
            continue
        py = dict(start=m.start(), end=m.end(), quote=m.group())
        break
    anchors = [u for u in claims if (re.search(AI, u['quote'], re.I) or any(re.search(AI,v['quote'],re.I) for v in group_context[u['group']])) and re.search(DETAIL, u['quote'], re.I)
                 and not re.search(r'AI.assisted development|AI coding assistants?|GitHub Copilot', u['quote'], re.I)]
    ai_groups = {u['group'] for u in anchors}
    ai_claims = [u for u in claims if u['group'] in ai_groups]
    reasons = []
    if not py:
        reasons.append('No evidence of Python stack')
    if not ai_claims:
        reasons.append('No AI/agentic project evidence')
    eligible = not reasons
    matched = [s for s in SKILLS if re.search(r'(?<![A-Za-z])'+re.escape(s)+r'(?![A-Za-z])', text, re.I)]
    scores = dict.fromkeys(WEIGHTS, 0)
    penalties = []
    if py:
        award('eligibility','Python evidence',0,py)
    if ai_claims:
        award('eligibility','AI implementation evidence',0,anchors[0])
    if eligible:
        scores['ai_project_depth'] = 8
        award('ai_project_depth','implemented AI system',8,anchors[0])
        for name, pattern, points in AI_FEATURES:
            match = next((u for u in ai_claims if re.search(pattern,u['quote'],re.I)),None)
            if match:
                scores['ai_project_depth'] += points
                award('ai_project_depth',name,points,match)
        py_impl = next((u for u in claims if re.search(r'\bPython\b|FastAPI|Flask|Django',u['quote'],re.I)),None)
        py_context = next((v for u in claims for v in group_context[u['group']] if re.search(r'\bPython\b',v['quote'],re.I)),None)
        if not py_impl and py_context:
            py_impl=py_context
        points = 10 if py_impl else 2
        scores['python_backend'] = points
        award('python_backend','Python implementation' if py_impl else 'Python skill only',points,py_impl or py)
        for category, rules in [('python_backend',BACKEND_FEATURES),('cloud_fullstack',CLOUD_FEATURES),('engineering_depth',ENGINEERING_FEATURES)]:
            for name,pattern,points in rules:
                match = next((u for u in claims if re.search(pattern,u['quote'],re.I)),None)
                if match:
                    scores[category] += points
                    award(category,name,points,match)
        depth_pattern = '|'.join(pattern for _,pattern,_ in AI_FEATURES)
        # A weak project cannot hide behind a deeper unrelated project: penalty is per
        # distinct weak claim, capped at 15 for the whole resume.
        weak = [u for u in ai_claims if re.search(r'chatbot|LLM|OpenAI|Gemini|GPT',u['quote'],re.I)
                and not any(re.search(depth_pattern+r'|business logic|document|format|user.defined|authentication|backend|FastAPI|Flask|Django|structured data|root cause|failure hook|watermark|dedup|RSS|speech|STT|TTS',v['quote'],re.I) for v in claims if v['group']==u['group'])]
        if weak:
            penalty = 10 if not any(re.search(depth_pattern,u['quote'],re.I) for u in ai_claims) else 5
            penalties.append(dict(points=penalty,reason='Thin LLM/API claim lacks workflow, retrieval, state, processing or backend implementation detail',
                                  start=weak[0]['start'],end=weak[0]['end'],quote=weak[0]['quote']))
        tutorial = next((u for u in ai_claims if re.search(r'tutorial|guided project|followed.*course',u['quote'],re.I)),None)
        if tutorial:
            penalties.append(dict(points=5,reason='Tutorial-style ownership is not demonstrated',**{k:tutorial[k] for k in ('start','end','quote')}))
    penalty_points = min(15,sum(p['points'] for p in penalties))
    total = max(0,sum(scores.values())-penalty_points) if eligible else 0
    strengths = [e['rule'] for e in evidence if e['points'] >= 4]
    return dict(eligible=eligible,rejection_reasons=reasons,matched_skills=matched,
                score_breakdown=scores,penalties=penalties,penalty_points=penalty_points,
                total_score=total,evidence=evidence,
                project_summary=ai_claims[0]['quote'][:500] if ai_claims else 'No qualifying AI implementation evidence found.',
                strengths=strengths,concerns=[p['reason'] for p in penalties] +
                (['Resume claims are not independently verified; heuristic scoring requires human review.'] if eligible else reasons))
