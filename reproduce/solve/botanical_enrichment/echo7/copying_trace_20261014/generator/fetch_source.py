"""Fetch a pinned, minimal author's source and Java-8 compatible compiler.

Budget: source < 1 MB; ECJ < 3 MB; compiled classes < 1 MB; ensemble
traces < 10 MB. No model arrays. Retain small traces and checks.
"""
import concurrent.futures
import hashlib
import json
from pathlib import Path
import urllib.request

HERE = Path(__file__).resolve().parent
COMMIT = 'a6ede2202dd7ad6285ce2c007bf22c2a0e7709b7'
BASE = f'https://raw.githubusercontent.com/TorstenTimm/SelfCitationTextgenerator/{COMMIT}/'

def fetch(path):
    content = urllib.request.urlopen(BASE + path).read()
    target = HERE / 'upstream' / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)
    return {'path': path, 'sha256': hashlib.sha256(content).hexdigest(), 'bytes': len(content)}

def main():
    tree = json.load(urllib.request.urlopen(f'https://api.github.com/repos/TorstenTimm/SelfCitationTextgenerator/git/trees/{COMMIT}?recursive=1'))
    paths = [x['path'] for x in tree['tree'] if (x['path'].startswith('source/src/') or x['path'] in ['LICENSE', 'README.md', 'PROPERTIES.md', 'executable/conf.properties', 'source/pom.xml']) and x['type'] == 'blob']
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        files = list(pool.map(fetch, paths))
    compiler_url = 'https://repo.maven.apache.org/maven2/org/eclipse/jdt/ecj/3.26.0/ecj-3.26.0.jar'
    compiler = urllib.request.urlopen(compiler_url).read()
    (HERE / 'ecj.jar').write_bytes(compiler)
    (HERE / 'source_manifest.json').write_text(json.dumps({'repository': 'https://github.com/TorstenTimm/SelfCitationTextgenerator', 'commit': COMMIT, 'files': files, 'compiler': {'url': compiler_url, 'sha256': hashlib.sha256(compiler).hexdigest()}}, indent=2), encoding='utf-8')
    print(f'Fetched {len(files)} files, {sum(x["bytes"] for x in files)} source bytes; compiler {len(compiler)} bytes')

if __name__ == '__main__':
    main()
