"""Assignment weights and explicit, reviewable sub-rules."""
WEIGHTS = dict(ai_project_depth=40, python_backend=30, cloud_fullstack=15,
               github=10, engineering_depth=5)
AI_FEATURES = [
    ('retrieval', r'retriev|semantic search|vector search|\bRAG\b', 6),
    ('embeddings', r'embedding|vector database|pgvector|FAISS|Chroma|Qdrant', 4),
    ('tools', r'tool.call|function.call|tool integration|MCP tools|tool execution', 5),
    ('state', r'checkpoint|session.memory|session persistence|conversational memory|shared (?:graph )?state|stateful|persistent (?:learner )?state|persistent memory|state management|persistent chat history', 5),
    ('orchestration', r'orchestrat|multi.agent|conditional rout|StateGraph|supervisor', 5),
    ('evaluation', r'evaluat|\bevals?\b|RAGAS|benchmark|model comparison|hyperparameter|fine.tun|quality checks', 4),
    ('data processing', r'preprocess|chunk|ingestion|data processing|feature engineering|data augmentation|document (?:parsing|processing)', 3),
]
BACKEND_FEATURES = [
    ('backend framework', r'FastAPI|Flask|Django', 8),
    ('async', r'\basync\b|asyncio|asynchronous', 4),
    ('PostgreSQL', r'PostgreSQL|Postgres\b', 4),
    ('Redis', r'\bRedis\b', 4),
]
CLOUD_FEATURES = [
    ('cloud', r'\bGCP\b|Google Cloud|\bAWS\b|Azure|Lambda|EC2|Cloudflare|DigitalOcean', 5),
    ('container', r'Docker|containeriz|Kubernetes', 4),
    ('deployment', r'deploy|CI/CD|continuous deployment|GitHub Actions', 4),
    ('frontend', r'React|Next\.js|frontend|front.end', 2),
]
ENGINEERING_FEATURES = [
    ('testing', r'\btests?\b|testing|pytest|JUnit|test suite', 1),
    ('architecture', r'architect|modular|microservice|schema.validat', 1),
    ('performance', r'cach|queue|concurren|parallel|Celery', 1),
    ('observability', r'observability|logging|tracing|monitoring|telemetry', 1),
    ('failure handling', r'failure|retry|fallback|error handling|exception handling', 1),
]
SKILLS = ['Python','JavaScript','TypeScript','Java','React','Next.js','FastAPI','Flask','Django',
          'PostgreSQL','Redis','LangChain','LangGraph','LlamaIndex','RAG','Docker','GCP','AWS',
          'TensorFlow','PyTorch','Scikit-learn','OpenAI','Gemini','MCP']
