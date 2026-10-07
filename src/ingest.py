"""Local parsing. No links from resumes are opened during extraction."""
import hashlib
import re
import unicodedata
from pathlib import Path
from urllib.parse import urlparse
from xml.etree import ElementTree
from zipfile import ZipFile


def normalize(text):
    text = unicodedata.normalize('NFKC', text).replace('\x00', ' ')
    # Recover extraction artifacts at known implementation verbs, not arbitrary words.
    text = re.sub(r'\b(Built|Developed|Deployed|Architected|Engineered|Integrated|Applied|Processed|Designed|Constructed|Provisioned|Rendered|Modeled|Structured|Enforced)(?=[a-z])',r'\1 ',text)
    lines=text.splitlines()
    normal=[line for line in lines if not re.search(r'(?:\b[A-Za-z]\s+){15,}',line)]
    if sum(len(line) for line in normal)>1500:
        text='\n'.join(normal)
    text = re.sub(r'([A-Za-z])-\s*\n\s*([a-z])', r'\1\2', text)
    # Remove display control characters, retain line boundaries.
    return '\n'.join(re.sub(r'[^\S\n]+', ' ', line).strip() for line in text.splitlines())


def quality(text):
    """Prefer text with ordinary words over character-by-character layout artifacts."""
    words = re.findall(r'[A-Za-z]+', text)
    return sum(len(w) for w in words if len(w) >= 3)


def extract(path):
    path = Path(path)
    result = dict(status='failed', text='', pages=[], links=[], warnings=[],
                  sha256=None, text_sha256=None, extraction_method=None)
    try:
        raw = path.read_bytes()
        result['sha256'] = hashlib.sha256(raw).hexdigest()
        suffix = path.suffix.lower()
        if suffix == '.pdf':
            from pypdf import PdfReader
            from io import BytesIO
            reader = PdfReader(BytesIO(raw), strict=False)
            if reader.is_encrypted and not reader.decrypt(''):
                raise ValueError('encrypted PDF')
            pages = []
            for page in reader.pages:
                pages.append(page.extract_text() or '')
                for ref in page.get('/Annots', []):
                    annotation = ref.get_object()
                    action = annotation.get('/A', {})
                    if hasattr(action, 'get_object'):
                        action = action.get_object()
                    uri = action.get('/URI')
                    if uri:
                        result['links'].append(str(uri))
            # Independent geometric parser helps columns, headings and spaced glyphs.
            try:
                import pdfplumber
                with pdfplumber.open(BytesIO(raw)) as doc:
                    alternative = [p.extract_text(x_tolerance=2, y_tolerance=3) or '' for p in doc.pages]
                # Preserve pypdf's block order unless geometry substantially repairs
                # spaced glyphs. More characters alone does not imply better columns.
                recovered = normalize('\n'.join(pages))
                mixed_spaced = bool(re.search(r'(?:\b[A-Za-z]\s+){15,}','\n'.join(pages))) and quality(recovered)>1500
                lines=[line for line in '\n'.join(pages).splitlines() if line.strip()]
                fragmented = sum(len(line.split())==1 for line in lines)/max(1,len(lines))>.4
                if not mixed_spaced and (quality('\n'.join(alternative)) > 1.15 * quality('\n'.join(pages)) or fragmented):
                    pages = alternative
                    result['extraction_method'] = 'pdfplumber'
                else:
                    result['extraction_method'] = 'pypdf'
            except Exception as exc:
                result['warnings'].append('Fallback parser unavailable: ' + type(exc).__name__)
                result['extraction_method'] = 'pypdf'
        elif suffix == '.docx':
            with ZipFile(path) as doc:
                xml = ElementTree.fromstring(doc.read('word/document.xml'))
                ns = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
                pages = ['\n'.join(''.join(t.text or '' for t in p.iter(ns+'t')) for p in xml.iter(ns+'p'))]
                rels = ElementTree.fromstring(doc.read('word/_rels/document.xml.rels')) if 'word/_rels/document.xml.rels' in doc.namelist() else []
                result['links'] = [r.attrib['Target'] for r in rels if r.attrib.get('TargetMode') == 'External']
            result['extraction_method'] = 'docx_xml'
        elif suffix == '.txt':
            pages = [raw.decode('utf-8-sig')]
            result['extraction_method'] = 'utf8'
        else:
            raise ValueError('unsupported file format')
        result['pages'] = [normalize(p) for p in pages]
        result['text'] = '\n'.join(result['pages'])
        empty = [i+1 for i,p in enumerate(result['pages']) if len(re.findall(r'[A-Za-z]',p)) < 20]
        if len(empty) == len(result['pages']):
            raise ValueError('empty or image-only document; OCR/manual review required')
        if empty:
            result['warnings'].append('Low-text pages '+str(empty)+'; inspect for blank/scanned content; extraction may be partial.')
        result['text_sha256'] = hashlib.sha256(re.sub(r'\s+', ' ', result['text']).encode()).hexdigest()
        result['links'] = sorted(set(result['links']))
        result['status'] = 'parsed'
    except Exception as exc:
        result['error'] = type(exc).__name__ + ': ' + str(exc)[:120]
    return result


def github_profiles(text, links):
    urls = list(links) + re.findall(r'(?:https?://)?(?:www\.)?github\.com/[A-Za-z0-9_./-]+', text, re.I)
    usernames = []
    for url in urls:
        if not url.startswith(('https://','http://')):
            url = 'https://' + url
        parsed = urlparse(url)
        if parsed.hostname not in ('github.com','www.github.com'):
            continue
        username = parsed.path.strip('/').split('/')[0]
        if re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?', username) and username.lower() not in ('topics','orgs','login','features','settings','search'):
            usernames.append(username)
    return list(dict.fromkeys(usernames))
