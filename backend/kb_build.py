"""KB builder: scans repository docs, creates embeddings via OpenAI, and saves metadata.

Usage:
  export OPENAI_API_KEY=...
  python backend/kb_build.py

Outputs saved to `backend/kb/`:
 - embeddings.npy  (N x D)
 - docs.json       (list of {'path', 'text'})
"""
import os
import json
import glob
import time

try:
    from openai import OpenAI
    import numpy as np
except Exception as e:
    print('Missing dependencies. Please install openai and numpy in backend requirements.')
    raise

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KB_DIR = os.path.join(ROOT, 'backend', 'kb')
if not os.path.exists(KB_DIR):
    os.makedirs(KB_DIR, exist_ok=True)

OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
if not OPENAI_API_KEY:
    raise RuntimeError('OPENAI_API_KEY must be set in environment to build KB')

client = OpenAI(api_key=OPENAI_API_KEY)

# files to index (text files and markdown)
INCLUDE = [
    os.path.join(ROOT, 'TECH_STACK_REPORT.md'),
    os.path.join(ROOT, 'EVALUATION_PLAN.md'),
    os.path.join(ROOT, 'README.md'),
    os.path.join(ROOT, 'NAVIGATION_GUIDE.md'),  # NEW: Navigation-specific training data
    # include backend and frontend important files
]

# also include many small source files under backend/modules
INCLUDE += glob.glob(os.path.join(ROOT, 'backend', 'modules', '*.py'))
INCLUDE = [p for p in INCLUDE if os.path.exists(p)]

print('Indexing files:')
for p in INCLUDE:
    print(' -', p)

docs = []
for path in INCLUDE:
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            text = f.read()
            docs.append({'path': os.path.relpath(path, ROOT), 'text': text})
    except Exception as e:
        print('Failed to read', path, e)

# chunking: for simplicity, split by 2000 chars
chunks = []
for d in docs:
    txt = d['text']
    start = 0
    while start < len(txt):
        chunk = txt[start:start+2000]
        chunks.append({'path': d['path'], 'text': chunk})
        start += 2000

print(f'Created {len(chunks)} chunks')

# create embeddings (OpenAI text-embedding-3-small or text-embedding-3-large depending on access)
EMB_MODEL = os.environ.get('OPENAI_EMBEDDING_MODEL', 'text-embedding-3-small')
embeddings = []
for i, c in enumerate(chunks):
    print(f'Embedding {i+1}/{len(chunks)}: {c["path"][:80]}...')
    try:
        resp = client.embeddings.create(model=EMB_MODEL, input=c['text'])
        emb = resp.data[0].embedding
        embeddings.append(emb)
    except Exception as e:
        print('Embedding error:', e)
        embeddings.append([0.0])
    time.sleep(0.1)

emb_np = np.array(embeddings, dtype=np.float32)
np.save(os.path.join(KB_DIR, 'embeddings.npy'), emb_np)
with open(os.path.join(KB_DIR, 'chunks.json'), 'w', encoding='utf-8') as f:
    json.dump(chunks, f, ensure_ascii=False, indent=2)

print('KB build complete. Saved to', KB_DIR)
 