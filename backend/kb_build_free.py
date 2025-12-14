"""KB builder using FREE sentence-transformers (no OpenAI needed).

Usage:
  python backend/kb_build_free.py

Outputs saved to `backend/kb/`:
 - embeddings.npy  (N x D)
 - chunks.json     (list of chunks)
"""
import os
import json
import glob

try:
    from sentence_transformers import SentenceTransformer
    import numpy as np
except Exception as e:
    print('Missing dependencies. Run: pip install sentence-transformers numpy')
    raise

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KB_DIR = os.path.join(ROOT, 'backend', 'kb')
if not os.path.exists(KB_DIR):
    os.makedirs(KB_DIR, exist_ok=True)

# files to index
INCLUDE = [
    os.path.join(ROOT, 'TECH_STACK_REPORT.md'),
    os.path.join(ROOT, 'EVALUATION_PLAN.md'),
    os.path.join(ROOT, 'README.md'),
    os.path.join(ROOT, 'NAVIGATION_GUIDE.md'),
]

INCLUDE += glob.glob(os.path.join(ROOT, 'backend', 'modules', '*.py'))
INCLUDE = [p for p in INCLUDE if os.path.exists(p)]

print('Indexing files:')
for p in INCLUDE:
    print(' -', os.path.relpath(p, ROOT))

docs = []
for path in INCLUDE:
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            text = f.read()
            docs.append({'path': os.path.relpath(path, ROOT), 'text': text})
    except Exception as e:
        print('Failed to read', path, e)

# chunk by 2000 chars
chunks = []
for d in docs:
    txt = d['text']
    start = 0
    while start < len(txt):
        chunk = txt[start:start+2000]
        chunks.append({'path': d['path'], 'text': chunk})
        start += 2000

print(f'Created {len(chunks)} chunks')

# Load free sentence-transformer model (all-MiniLM-L6-v2 is small and fast)
print('Loading sentence-transformer model (one-time download)...')
model = SentenceTransformer('all-MiniLM-L6-v2')
print('✅ Model loaded')

# Create embeddings locally
print('Creating embeddings...')
embeddings = []
texts = [c['text'] for c in chunks]

# Batch encode for efficiency
embeddings_list = model.encode(texts, show_progress_bar=True)
embeddings = np.array(embeddings_list, dtype=np.float32)

print(f'✅ Created {len(embeddings)} embeddings')

# Save
emb_path = os.path.join(KB_DIR, 'embeddings.npy')
chunks_path = os.path.join(KB_DIR, 'chunks.json')

np.save(emb_path, embeddings)
with open(chunks_path, 'w', encoding='utf-8') as f:
    json.dump(chunks, f, indent=2)

print(f'✅ KB saved to {KB_DIR}')
print(f'   - embeddings.npy: {embeddings.shape}')
print(f'   - chunks.json: {len(chunks)} chunks')
