/*
 * Runs SailPy's Python code in the browser.
 *
 * This Web Worker (a module worker) loads Pyodide (CPython compiled to WebAssembly), copies the
 * files from python/ into its virtual file system and then answers calls like
 * {fn: 'hull.resistance_comparison', args: {...}} from js/app.js. Running in a
 * worker keeps the page responsive while an optimization is running.
 */
import { loadPyodide } from '../vendor/pyodide/pyodide.mjs';

const ROOT = new URL('../', self.location.href).href;
const PYODIDE_URL = ROOT + 'vendor/pyodide/';

// Every Python file the app needs (paths relative to python/)
const PY_FILES = [
  'functions/npcompat.py',
  'functions/resistance.py',
  'functions/resistance_added.py',
  'functions/minpack.py',
  'functions/vpp.py',
  'web/go.py',
  'web/hull.py',
  'web/optimization.py',
  'web/results.py',
  'web/appendages.py',
  'web/api.py',
];
const WHEELS = ['vendor/Platypus_Opt-1.4.1-py3-none-any.whl'];


let api = null;

async function start() {
  let pyodide;
  try {
    pyodide = await loadPyodide({ indexURL: PYODIDE_URL });
  } catch (err) {
    throw new Error('Could not start Pyodide from vendor/pyodide/: ' + (err && err.message || err));
  }
  const home = '/home/pyodide/sailpy';
  pyodide.FS.mkdirTree(home + '/functions');
  pyodide.FS.mkdirTree(home + '/web');

  const texts = await Promise.all(PY_FILES.map(async (f) => {
    const r = await fetch(ROOT + 'python/' + f, { cache: 'no-cache' });
    if (!r.ok) throw new Error('Could not download python/' + f + ' (HTTP ' + r.status + '). Check that this file was uploaded to the repository.');
    return r.text();
  }));
  PY_FILES.forEach((f, i) => pyodide.FS.writeFile(home + '/' + f, texts[i]));

  for (const w of WHEELS) {
    const r = await fetch(ROOT + 'python/' + w);
    if (!r.ok) throw new Error('Could not download python/' + w + ' (HTTP ' + r.status + ')');
    pyodide.unpackArchive(await r.arrayBuffer(), 'wheel');
  }

  self.sailpyProgress = (done, total) => postMessage({ type: 'progress', done, total });
  pyodide.runPython(`
import sys
sys.path.insert(0, '${home}')
import js
from web import api
api.set_progress(js.sailpyProgress)
`);
  api = pyodide.pyimport('web.api');
}

const ready = start().then(
  () => postMessage({ type: 'ready' }),
  (err) => postMessage({ type: 'fatal', error: String(err && err.message || err) }),
);

self.onmessage = async (event) => {
  const { id, fn, args } = event.data;
  try {
    await ready;
    if (!api) throw new Error('Python engine failed to start');
    const out = api.call(fn, JSON.stringify(args || {}));
    postMessage({ type: 'result', id, result: JSON.parse(out) });
  } catch (err) {
    let message = String(err && err.message || err);
    // keep only the last lines of a Python traceback
    const lines = message.trim().split('\n');
    postMessage({ type: 'result', id, error: lines.slice(-3).join('\n') });
  }
};
