/*
 * SailPy - static web version.
 *
 * The page layout and interactions live here; every engineering calculation
 * (resistance, optimization, appendage sizing, the figures) is done by the
 * Python code in python/, which runs in the browser via js/engine-worker.js.
 * Each Python function corresponds to a callback of the original Dash app.
 */
'use strict';

/* ------------------------------------------------------------------ helpers */

function h(tag, props, ...children) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(props || {})) {
    if (v === undefined || v === null || v === false) continue;
    if (k === 'class') el.className = v;
    else if (k === 'style' && typeof v === 'object') Object.assign(el.style, v);
    else if (k.startsWith('on') && typeof v === 'function') el.addEventListener(k.slice(2), v);
    else if (k === 'html') el.innerHTML = v;
    else el.setAttribute(k, v === true ? '' : v);
  }
  for (const c of children.flat(Infinity)) {
    if (c === null || c === undefined || c === false) continue;
    el.append(c instanceof Node ? c : document.createTextNode(String(c)));
  }
  return el;
}

const $ = (sel, root = document) => root.querySelector(sel);
const debounce = (fn, ms) => { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); }; };
const isNumber = (v) => v !== '' && v !== null && v !== undefined && isFinite(Number(v));

const PLOT_CONFIG = { responsive: true, displaylogo: false };

/* ------------------------------------------------------------- the engine */

// Each engine is a Web Worker running Python (js/engine-worker.js).
function makeEngine(onStatus) {
  const worker = new Worker('js/engine-worker.js', { type: 'module' });
  const pending = new Map();
  let nextId = 1;
  let progressHandler = null;
  let resolveReady, rejectReady;
  const ready = new Promise((res, rej) => { resolveReady = res; rejectReady = rej; });
  ready.catch(() => {});

  worker.onmessage = (event) => {
    const msg = event.data;
    if (msg.type === 'ready') { resolveReady(); onStatus('ready'); }
    else if (msg.type === 'fatal') {
      rejectReady(new Error(msg.error));
      for (const p of pending.values()) p.reject(new Error(msg.error));
      pending.clear();
      onStatus('failed', msg.error);
    }
    else if (msg.type === 'progress') { if (progressHandler) progressHandler(msg.done, msg.total); }
    else if (msg.type === 'result') {
      const p = pending.get(msg.id);
      pending.delete(msg.id);
      if (!p) return;
      if (msg.error) p.reject(new Error(msg.error)); else p.resolve(msg.result);
    }
  };
  worker.onerror = (e) => onStatus('failed', e.message || 'worker error');

  function call(fn, args) {
    const id = nextId++;
    return new Promise((resolve, reject) => {
      pending.set(id, { resolve, reject });
      worker.postMessage({ id, fn, args });
    });
  }

  // For calls fired while typing: only the newest answer for a given key is used
  const latest = {};
  function callLatest(key, fn, args) {
    const ticket = (latest[key] || 0) + 1;
    latest[key] = ticket;
    return call(fn, args).then((r) => {
      if (latest[key] !== ticket) throw Object.assign(new Error('stale'), { stale: true });
      return r;
    });
  }

  return { call, callLatest, ready, onProgress: (f) => { progressHandler = f; } };
}

// main engine: every calculation of the page
const Engine = makeEngine((status, detail) => setEngineStatus(status, detail));

// a second engine, started the first time a polar diagram is requested, so the
// VPP (a few seconds) never makes the rest of the page wait
let vppEngine = null;
function getVppEngine() {
  if (!vppEngine) vppEngine = makeEngine(() => {});
  return vppEngine;
}

function setEngineStatus(status, detail) {
  const badge = $('[data-engine-badge]');
  const note = $('[data-engine-status]');
  if (status === 'ready') {
    badge.textContent = 'Python: ready';
    badge.className = 'badge engine-badge ready';
    note.textContent = '';
  } else if (status === 'failed') {
    badge.textContent = 'Python: failed';
    badge.className = 'badge engine-badge failed';
    badge.title = detail || '';
    note.textContent = 'The Python engine could not start: ' + (detail || '') + '. Try reloading the page.';
    const box = $('#engine-error');
    box.replaceChildren(h('div', { class: 'alert alert-danger mb-0' },
      h('strong', {}, 'The Python engine could not start. '),
      'The calculations will not work until this is fixed. Details: ',
      h('code', { style: { whiteSpace: 'pre-wrap' } }, detail || 'unknown error')));
    box.hidden = false;
  }
}

/* ------------------------------------------------------------------ state */

const STORAGE_KEY = 'sailpy-state-v1';

const DEFAULT_STATE = {
  hull: {
    lwl: '10', bwl: '3.17', tc: '0.57', disp: '8.17', lcb: '5', lcf: '4', cm: 0.7, cp: 0.58, cwp: 0.75,
    lwl2: '10', bwl2: '3.17', tc2: '0.57', disp2: '8.17', lcb2: '5', lcf2: '4', cm2: 0.7, cp2: 0.58, cwp2: 0.75,
  },
  // hull #1, used as the starting point of the optimization (dimensions.json)
  dimensions: { bwl: '3.17', cm: 0.7, cp: 0.58, cwp: 0.75, disp: '8.17', lcb: '5', lcf: '4', lwl: '10', tc: '0.57' },
  ga: {
    gamethod: 'NSGAII', offsprings: '300', capsize: '2', weight1: 5, weight2: 5,
    velocity: [3, 5], heel: [2, 3], height: [1, 3], angle: [120, 160], length: [1, 1.5],
  },
  results: null, // {rows, gamethod} of the last optimization; null = example run
  axes: { y: 'Resistance', x: 'Comfort' },
  selectedId: 1,
  selectedHull: { bwl: 3.17, disp: 8.17, lcb: 5.0, lcf: 4.0, lwl: 10.0, tc: 0.57 }, // dimensions-hull.json
  appendages: null, // {hullKey, values}
};

let state = loadState();
let exampleResults = null; // the optimization shipped with the app (data/optimizationresistance.csv)

function loadState() {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY));
    if (saved && typeof saved === 'object') return Object.assign(structuredClone(DEFAULT_STATE), saved);
  } catch (e) { /* storage unavailable */ }
  return structuredClone(DEFAULT_STATE);
}

const saveState = debounce(() => {
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(state)); } catch (e) { /* storage unavailable or full */ }
}, 300);

function currentResults() {
  return state.results || exampleResults;
}

/* ------------------------------------------------------- results CSV I/O */

const COLUMNS = ['id', 'Resistance', 'Rv', 'Ri', 'Rr', 'Rincli', 'Comfort', 'CS', 'LWL', 'BWL', 'Draft',
  'Displacement', 'AWP', 'LCB', 'LCF', 'constraint1', 'constraint2', 'constraint3', 'constraint4',
  'constraint5', 'valid'];

function parseResultsCsv(text) {
  const lines = text.trim().split(/\r?\n/);
  const header = lines[0].split(',');
  return lines.slice(1).map((line) => {
    const cells = line.split(',');
    const row = {};
    header.forEach((col, i) => {
      const v = cells[i];
      if (v === 'True' || v === 'False') row[col] = v === 'True';
      else row[col] = col === 'id' ? parseInt(v, 10) : parseFloat(v);
    });
    return row;
  });
}

function resultsToCsv(rows) {
  const out = [COLUMNS.join(',')];
  for (const r of rows) {
    out.push(COLUMNS.map((c) => {
      const v = r[c];
      if (typeof v === 'boolean') return v ? 'True' : 'False';
      if (c === 'id') return String(v);
      return Number(v).toFixed(4);
    }).join(','));
  }
  return out.join('\n') + '\n';
}

function download(filename, text) {
  const url = URL.createObjectURL(new Blob([text], { type: 'text/csv' }));
  const a = h('a', { href: url, download: filename });
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

/* ---------------------------------------------------------------- widgets */

function textInput(id, value, onChange, cls = '') {
  const input = h('input', { type: 'text', id, class: 'form-control form-control-sm ' + cls, value });
  input.addEventListener('input', () => {
    input.classList.toggle('input-invalid', !isNumber(input.value));
    onChange(input.value);
  });
  return input;
}

function select(id, options, value, onChange, style) {
  const el = h('select', { id, class: 'form-select form-select-sm', style },
    options.map(([v, label]) => h('option', { value: v, selected: String(v) === String(value) }, label)));
  el.addEventListener('change', () => onChange(el.value));
  return el;
}

/**
 * Slider with tick labels (dcc.Slider / dcc.RangeSlider in the Dash version).
 * marks: {value: label}; start: number or [low, high].
 */
function slider({ id, min, max, step, start, marks, onChange, label }) {
  const holder = h('div', { id });
  const valueLabel = h('div', { class: 'slider-value' });
  const block = h('div', { class: 'slider-block' }, label ? valueLabel : null, holder);
  const values = Object.keys(marks).map(Number);
  noUiSlider.create(holder, {
    start,
    connect: Array.isArray(start) ? true : [true, false],
    step,
    range: { min, max },
    pips: { mode: 'values', values, density: 100, format: { to: (v) => marks[v] ?? marks[String(v)] ?? '' } },
  });
  const read = () => {
    const v = holder.noUiSlider.get(true);
    return Array.isArray(v) ? v.map((x) => Number(x.toFixed(4))) : Number(v.toFixed(4));
  };
  const update = () => { if (label) valueLabel.textContent = label(read()); };
  holder.noUiSlider.on('update', update);
  holder.noUiSlider.on('change', () => { update(); onChange(read()); });
  update();
  return block;
}

function graph(id, height) {
  return h('div', { id, class: 'graph-placeholder', style: { minHeight: (height || 300) + 'px' } }, 'Calculating…');
}

function drawFigure(el, figure) {
  if (!el || !el.isConnected) return;
  el.classList.remove('graph-placeholder');
  if (el.dataset.plotted) Plotly.react(el, figure.data, figure.layout, PLOT_CONFIG);
  else { el.textContent = ''; Plotly.newPlot(el, figure.data, figure.layout, PLOT_CONFIG); el.dataset.plotted = '1'; }
}

function showGraphError(el, err) {
  if (!el || !el.isConnected || err.stale) return;
  let note = el.nextElementSibling;
  if (!note || !note.classList.contains('graph-error')) {
    note = h('div', { class: 'graph-error' });
    el.after(note);
  }
  note.textContent = err ? 'Could not update: ' + err.message : '';
  if (!err) note.remove();
}

function clearGraphError(el) {
  const note = el && el.nextElementSibling;
  if (note && note.classList.contains('graph-error')) note.remove();
}

function simpleTable(table) {
  return h('table', { class: 'simple-table' },
    h('thead', {}, h('tr', {}, table.columns.map((c) => h('th', {}, c)))),
    h('tbody', {}, table.rows.map((r) => h('tr', {}, r.map((v) => h('td', {}, v))))));
}

/* ------------------------------------------------------------- tab: intro */

function renderIntroduction(root) {
  const step = (icon, text) => h('div', { class: 'col' }, h('i', { class: icon + ' fa-2x icon-big' }), h('p', {}, text));
  root.append(h('div', { class: 'container mt-4' }, h('div', { class: 'row' },
    h('div', { class: 'col-md-6 justify' },
      h('h4', {}, 'Summary'),
      h('p', {}, 'This application provides a comprehensive set of tools that allow the user to design a sailboat aiming to improve performance from the very beginning. For doing so, the application applies a parametric model of the hull that allows easy manipulation through a small number of parameters in order to generate new study objects. At the first stage, the hull is optimized towards the minimum resistance computed in several heel angles and velocities, whilst respecting constraints of safety and comfort. A Genetic Algorithm is responsible to carry out the optimization phase using default or custom parameters. After finished, all the hulls generated are displayed and the user can choose which is the most suitable. Based on one hull selected, the analyzes process allows the inclusion of appendages, namely keel and rudder, and sails. A first draft for the final sailboat can be drawn by the user. At this phase, a Velocity Prediction Program is applied to compute an estimation for velocity for differnt wind conditions. After the analysis is completed, the user may view and export the dimensions set for the entire sailboat.'),
      h('div', {}, h('a', { href: 'assets/Thesis.pdf', download: 'Thesis.pdf' }, 'Read More'))),
    h('div', { class: 'col-md-6' },
      h('h4', {}, 'How it works'), h('br'),
      h('div', { class: 'row text-center' },
        step('icon-tools', 'Set the hull dimensions that will serve as a starting point'),
        step('icon-adjustments', 'Configure the genetic algorithm and the parameters to be optimized'),
        step('icon-speedometer', 'Run the optimization. It might take some time')),
      h('br'),
      h('div', { class: 'row text-center' },
        step('icon-bargraph', 'Choose one hull based on the least resistance performance'),
        step('icon-refresh', 'Include appendages and sails'),
        step('icon-search', 'View the outcome and export the best individuals'))))));
}

/* -------------------------------------------------------------- tab: hull */

function renderHull(root) {
  const s = state.hull;
  const chart = graph('resistance-comparison', 500);

  const update = debounce(() => {
    const args = {};
    for (const k of ['lwl', 'bwl', 'tc', 'cm', 'cp', 'cwp', 'lcb', 'lcf', 'disp']) {
      args[k] = s[k];
      args[k + '2'] = s[k + '2'];
    }
    if (!Object.values(args).every(isNumber)) return;
    Engine.callLatest('hull', 'hull.resistance_comparison', args).then((r) => {
      drawFigure(chart, r.figure);
      clearGraphError(chart);
      state.dimensions = r.dimensions;
      saveState();
    }, (err) => showGraphError(chart, err));
  }, 250);

  const set = (key) => (value) => { s[key] = value; saveState(); update(); };
  const dimensionInputs = (sfx) => [
    ['lwl', 'Waterline Length [m]'], ['bwl', 'Waterline Beam [m]'], ['tc', 'Draft Canoe Body [m]'],
    ['disp', 'Displacement [m3]'], ['lcb', 'Longitudinal Centre of Buoyancy (LCB) [m]'],
    ['lcf', 'Longitudinal Centre of Flotation (LCF) [m]'],
  ].map(([k, label]) => [h('label', { for: k + sfx }, label), textInput(k + sfx, s[k + sfx], set(k + sfx))]);

  const coefficientSliders = (sfx) => [
    h('label', {}, 'Midsection Coefficient'),
    slider({ id: 'cm' + sfx, min: 0.65, max: 0.78, step: 0.01, start: s['cm' + sfx], label: (v) => v.toFixed(2),
      marks: { 0.65: '0.65', 0.68: '0.68', 0.71: '0.71', 0.74: '0.74', 0.78: '0.78' }, onChange: set('cm' + sfx) }),
    h('label', {}, 'Prismatic Coefficient'),
    slider({ id: 'cp' + sfx, min: 0.52, max: 0.6, step: 0.01, start: s['cp' + sfx], label: (v) => v.toFixed(2),
      marks: { 0.52: '0.52', 0.54: '0.54', 0.56: '0.56', 0.58: '0.58', 0.6: '0.60' }, onChange: set('cp' + sfx) }),
    h('label', {}, 'Waterplane Area Coefficient'),
    slider({ id: 'cwp' + sfx, min: 0.65, max: 0.9, step: 0.01, start: s['cwp' + sfx], label: (v) => v.toFixed(2),
      marks: { 0.65: '0.65', 0.7: '0.70', 0.8: '0.80', 0.9: '0.90' }, onChange: set('cwp' + sfx) }),
  ];

  root.append(h('div', { class: 'container mt-4' }, h('div', { class: 'row' },
    h('div', { class: 'col-md-4 justify' },
      h('h4', {}, 'Main parameters'),
      h('p', {}, 'The first stage of the analysis is setting the main dimensions of the hull. The boat #1 dimensions will be used further in the analysis, whereas the boat #2 can be used to investigate new solutions to reduce resitance.')),
    h('div', { class: 'col-md-8' },
      h('h4', {}, 'Main Dimensions'),
      h('div', { class: 'row regularfont' },
        h('div', { class: 'col-md-5' }, h('h5', {}, 'Hull #1'), dimensionInputs('')),
        h('div', { class: 'col-md-2' }),
        h('div', { class: 'col-md-5' }, h('h5', {}, 'Hull #2 [Experiment]'), dimensionInputs('2'))),
      h('br'),
      h('h4', {}, 'Form Coefficients'),
      h('div', { class: 'row regularfont' },
        h('div', { class: 'col-md-5' }, coefficientSliders('')),
        h('div', { class: 'col-md-2' }),
        h('div', { class: 'col-md-5' }, coefficientSliders('2'))),
      h('br'),
      h('h4', {}, 'Resistance comparison'),
      chart))));
  update();
}

/* ------------------------------------------------------- tab: optimization */

const GA_METHODS = [
  ['NSGAII', 'NSGAII - Nondominated Sorting Genetic Algorithm'],
  ['GDE3', 'GDE3 - Generalized Differential Evolution'],
  ['OMOPSO', 'OMOPSO - Multi-Objective Particle Swarm Optimization'],
  ['SMPSO', 'SMPSO - Speed-Constrained Particle Swarm Optimization'],
  ['SPEA2', 'SPEA2 - Strength Pareto Evolutionary Algorithm'],
  ['EpsMOEA', 'MOEA -  Multi-Objective Evolutionary Algorithm'],
];

let optimizationRunning = false;

function renderOptimization(root) {
  const g = state.ga;
  const setGa = (key) => (value) => { g[key] = value; saveState(); };
  const range = (n0, n1, f) => Object.fromEntries(Array.from({ length: n1 - n0 + 1 }, (_, i) => [n0 + i, f(n0 + i)]));

  const limitsBox = h('div', { id: 'dimensions-limits' }, h('div', { class: 'graph-placeholder', style: { minHeight: '120px' } }, 'Calculating…'));
  const runButton = h('button', { id: 'export-ga', type: 'button', class: 'btn btn-outline-dark btn-sm' }, 'Run optimization');
  const output = h('div', { id: 'output-button' });

  const limitInput = (id, value) => h('input', { type: 'text', id, value, class: 'form-control form-control-sm',
    oninput: (e) => e.target.classList.toggle('input-invalid', !isNumber(e.target.value)) });

  Engine.callLatest('limits', 'optimization.dimension_limits', { dimensions: state.dimensions }).then((lim) => {
    const v = lim.values;
    const pair = (label, a, current, b) => [
      h('label', {}, label),
      h('div', { class: 'limit-row' }, limitInput(a, v[a]), h('p', {}, current), limitInput(b, v[b]))];
    const single = (label, id) => [h('label', {}, label), h('div', { class: 'limit-row' }, limitInput(id, v[id]))];
    limitsBox.replaceChildren(h('div', { class: 'row' },
      h('div', { class: 'col-sm-6' },
        pair('Waterline length', 'lwl-min', lim.current.lwl, 'lwl-max'),
        pair('Waterline beam', 'bwl-min', lim.current.bwl, 'bwl-max'),
        pair('Draft', 'tc-min', lim.current.tc, 'tc-max'),
        single('Displacement [m3]', 'displac'),
        single('Radius of gyration / waterline length [m]', 'gyration'),
        single('Ballast Ratio [%]', 'ballast-ratio')),
      h('div', { class: 'col-sm-6' },
        pair('LCB', 'lcb-min', lim.current.lcb, 'lcb-max'),
        pair('LCF', 'lcf-min', lim.current.lcf, 'lcf-max'),
        pair('Waterplane Coefficient (Cwp)', 'cwp-min', ' - ', 'cwp-max'),
        pair('Prismatic Coefficient (Cp)', 'cp-min', ' - ', 'cp-max'),
        pair('Midship Area Coefficient (Cm)', 'cm-min', ' - ', 'cm-max'))));
  }, (err) => { if (!err.stale) limitsBox.textContent = 'Could not compute the limits: ' + err.message; });

  runButton.addEventListener('click', () => runOptimization(runButton, output));
  if (optimizationRunning) { runButton.disabled = true; runButton.textContent = 'Running... please wait'; }

  root.append(h('div', { class: 'container' },
    h('div', { class: 'row' },
      h('div', { class: 'col-md-6 justify mt-4' },
        h('h4', {}, 'Genetic Algorithm Configuration'),
        h('p', {}, 'The optimizaton method can be choosen between a default method, in which all the parameters are automatically set based on the literature best recommendations, and a custom method. The latter applies the algorithm NSGA II - Nondominated Sorting Genetic Algorithm developed by Professor Kalyanmoy Deb. It needs seven parameters to be configured. In case you are not familiar with them, more details are provided when hoving the parameters or reading the documentation in the link below. In any case, the standard configuration will provide satisfactory results.'),
        h('h4', {}, 'Optimization Parameters'),
        h('label', { for: 'ga-method' }, 'Method'),
        select('ga-method', GA_METHODS, g.gamethod, setGa('gamethod'), { width: '70%' }),
        h('label', { for: 'offsprings-platypus' }, 'Number of offsprings'),
        h('input', { type: 'number', id: 'offsprings-platypus', value: g.offsprings, min: 10, step: 10,
          class: 'form-control form-control-sm', style: { width: '100px' }, oninput: (e) => setGa('offsprings')(e.target.value) }),
        h('br'),
        h('label', {}, 'Behave of each algorithm'),
        h('img', { src: 'assets/static/platypus3.png', width: '100%', alt: 'How each algorithm explores the search space' }),
        h('br'), h('br'),
        h('h4', {}, 'Constraints'),
        h('p', {}, 'Constraints help maintain the sailboats feasible. The Capsize Screening Factor empirically evaluates the likelihood of capsizing based on the formula shown below. Another constraint is the displacement, which assits the optimization process on not allowing unrealistic hulls.'),
        h('img', { src: 'assets/static/cs.png', height: '28', alt: 'CS = BWL*1.1 / displacement^(1/3)' }),
        h('br'),
        h('label', { for: 'capsize-factor' }, 'Capsize Screening Factor'),
        h('input', { type: 'number', id: 'capsize-factor', value: g.capsize, class: 'form-control form-control-sm',
          style: { width: '80px' }, oninput: (e) => setGa('capsize')(e.target.value) })),
      h('div', { class: 'col-md-6 justify mt-4' },
        h('h4', {}, 'Weighted Objectives'),
        h('p', {}, 'Two objectives will be analyzed for the bare hull: resistance and added resistance in waves. They are determined under different conditions of heel and velocity that the user can set through the sliders below. The objectives can be distinguished in terms of importance, which is proportional to its value. Besides that, in case you want to ignore an objective, set its value to zero.'),
        h('div', { class: 'row' },
          h('div', { class: 'col' }, slider({ id: 'weight1', min: 0, max: 10, step: 1, start: g.weight1, onChange: setGa('weight1'),
            label: (v) => 'Still water resistance: ' + v, marks: { 0: '0', 2: '2', 4: '4', 6: '6', 8: '8', 10: '10' } })),
          h('div', { class: 'col' }, slider({ id: 'weight2', min: 0, max: 10, step: 1, start: g.weight2, onChange: setGa('weight2'),
            label: (v) => 'Added resistance: ' + v, marks: { 0: '0', 2: '2', 4: '4', 6: '6', 8: '8', 10: '10' } }))),
        h('h4', {}, 'Study case'),
        h('p', {}, 'The parameters below describe the expected operational profile of the boat and the expected sea conditions.'),
        h('label', {}, 'Velocities analyzed'),
        slider({ id: 'velocity-range', min: 2, max: 7, step: 1, start: g.velocity, onChange: setGa('velocity'), marks: range(2, 7, (i) => i + ' knots') }),
        h('label', {}, 'Heel angles analyzed'),
        slider({ id: 'heel-range', min: 0, max: 5, step: 1, start: g.heel, onChange: setGa('heel'), marks: range(0, 5, (i) => i * 10 + ' deg') }),
        h('label', {}, 'Wave height'),
        slider({ id: 'height_range', min: 0, max: 5, step: 1, start: g.height, onChange: setGa('height'), marks: range(0, 5, (i) => i + ' m') }),
        h('label', {}, 'Wave angle'),
        slider({ id: 'angle_range', min: 100, max: 180, step: 1, start: g.angle, onChange: setGa('angle'),
          marks: { 100: '100 deg', 120: '120 deg', 140: '140 deg', 160: '160 deg', 180: '180 deg' } }),
        h('label', {}, 'Wave length as fraction of ship length'),
        slider({ id: 'length_range', min: 0.5, max: 4, step: 0.5, start: g.length, onChange: setGa('length'),
          marks: { 0.5: '0.5', 1: '1.0', 1.5: '1.5', 2: '2.0', 2.5: '2.5', 3: '3.0', 3.5: '3.5', 4: '4.0' } }),
        h('h4', {}, 'Dimensions optimized'),
        h('p', {}, 'The limits of each dimension optimized at this stage can be set below. Standard values are recommended, but they can be stretched to explore more widely the dimensions space. The algorithm will evaluate which solutions are feasible and automatically exclude the ones that do not fit the criteria. Bear in mind that the values of minimum and maximum may affect performance and convergence.'),
        limitsBox)),
    h('div', { class: 'row' }, h('div', { class: 'col text-center mt-4' },
      h('p', {}, 'Press the button below and wait for the confirmation. The optimization runs on your own computer, so the page stays usable while it works.'),
      runButton, h('br'), h('br'), output))));
}

async function runOptimization(button, output) {
  const g = state.ga;
  const ids = ['lwl-min', 'lwl-max', 'bwl-min', 'bwl-max', 'tc-min', 'tc-max', 'lcb-min', 'lcb-max', 'lcf-min', 'lcf-max',
    'displac', 'cwp-min', 'cwp-max', 'cp-min', 'cp-max', 'cm-min', 'cm-max'];
  const limits = {};
  for (const id of ids) {
    const el = document.getElementById(id);
    if (!el || !isNumber(el.value)) {
      output.replaceChildren(h('div', { class: 'alert alert-warning' }, 'Please check the dimension limits: every box needs a number.'));
      return;
    }
    limits[id.replace('-', '')] = Number(el.value);
  }
  if (!isNumber(g.offsprings) || Number(g.offsprings) < 1) {
    output.replaceChildren(h('div', { class: 'alert alert-warning' }, 'Please enter the number of offsprings.'));
    return;
  }

  optimizationRunning = true;
  button.disabled = true;
  button.textContent = 'Running... please wait';
  const bar = h('div', { class: 'progress-bar', role: 'progressbar', style: { width: '0%' } });
  const label = h('div', { class: 'small text-muted mt-1' }, 'Starting…');
  output.replaceChildren(h('div', { class: 'mx-auto', style: { maxWidth: '420px' } }, h('div', { class: 'progress' }, bar), label));
  const t0 = performance.now();
  Engine.onProgress((done, total) => {
    const pct = Math.min(100, Math.round(100 * done / total));
    bar.style.width = pct + '%';
    label.textContent = `${done} of about ${total} offsprings evaluated · ${((performance.now() - t0) / 1000).toFixed(0)} s`;
  });

  try {
    const res = await Engine.call('optimization.run', {
      dimensions: state.dimensions,
      settings: { offsprings: g.offsprings, gamethod: g.gamethod, velocityrange: g.velocity, heelrange: g.heel, limits },
    });
    state.results = { rows: res.rows, gamethod: res.gamethod };
    state.selectedId = 1;
    const first = res.rows[0];
    state.selectedHull = { lwl: first.LWL, bwl: first.BWL, tc: first.Draft, disp: first.Displacement, lcb: first.LCB, lcf: first.LCF };
    saveState();
    const done = h('div', { class: 'alert alert-success' }, res.message + '. ',
      h('a', { href: '#application/results' }, 'See the results'));
    if (output.isConnected) output.replaceChildren(done);
    else lastOptimizationMessage = done;
  } catch (err) {
    const fail = h('div', { class: 'alert alert-danger' }, 'The optimization stopped: ' + err.message);
    if (output.isConnected) output.replaceChildren(fail); else lastOptimizationMessage = fail;
  } finally {
    optimizationRunning = false;
    Engine.onProgress(null);
    const b = document.getElementById('export-ga');
    if (b) { b.disabled = false; b.textContent = 'Run optimization'; }
  }
}
let lastOptimizationMessage = null;

/* ------------------------------------------------------------ tab: results */

const AXES = [
  ['Resistance', 'Still water resistance'], ['Comfort', 'Added resistance'], ['LWL', 'Waterline length'],
  ['BWL', 'Waterline beam'], ['Draft', 'Draft'], ['Displacement', 'Displacement'], ['AWP', 'Waterplane area'],
  ['LCB', 'LCB'], ['LCF', 'LCF'],
];
const TABLE_COLUMNS = COLUMNS.slice(0, COLUMNS.indexOf('LCF') + 1);

function renderResults(root) {
  const results = currentResults();
  if (!results) {
    root.append(h('div', { class: 'container mt-4' }, h('p', {}, 'Loading the results…')));
    return;
  }
  const rows = results.rows;
  const main = graph('output-optimization', 500);
  const bar = graph('plot-resistance-individual', 600);
  const chosen = h('div', { id: 'export-hull-dimensions' });
  const tableBox = h('div', { id: 'table-all-individuals' });
  const barsBox = h('div', { id: 'plot-dimensions' });
  const selectedRows = new Set();

  Engine.call('rows.set', { rows });

  const drawMain = () => Engine.callLatest('scatter', 'results.scatter', {
    rows: 'current', resultshullaxisy: state.axes.y, resultshullaxisx: state.axes.x, gamethod: results.gamethod,
  }).then((fig) => { drawFigure(main, fig); attachHover(); }, (err) => showGraphError(main, err));

  const choose = (id) => {
    Engine.callLatest('bar', 'results.resistance_bar', { rows: 'current', hover: id })
      .then((fig) => drawFigure(bar, fig), (err) => showGraphError(bar, err));
    Engine.callLatest('chosen', 'results.selected_hull', { rows: 'current', index: id }).then((sel) => {
      state.selectedId = sel.id;
      state.selectedHull = sel.hull;
      saveState();
      chosen.replaceChildren(...sel.text.map((t) => h('p', { style: { paddingLeft: '20px', display: 'inline-block' } }, t)));
    }, () => {});
  };

  let hooked = false;
  function attachHover() {
    if (hooked) return;
    hooked = true;
    // hovering (or clicking) an individual selects it, as in the Dash version
    const pick = (ev) => {
      const pt = ev.points && ev.points[0];
      if (pt && pt.customdata !== undefined && pt.customdata !== null) choose(pt.customdata);
    };
    main.on('plotly_hover', pick);
    main.on('plotly_click', pick);
  }

  const drawBars = () => Engine.callLatest('dimbars', 'results.dimension_bars', { rows: 'current', selected_ids: [...selectedRows] })
    .then((figs) => {
      if (!barsBox.isConnected) return;
      barsBox.replaceChildren();
      figs.forEach((fig) => { const d = h('div'); barsBox.append(d); Plotly.newPlot(d, fig.data, fig.layout, PLOT_CONFIG); });
    }, () => {});

  // table of valid individuals with sorting and row selection
  let sortCol = 'id';
  let sortDir = 1;
  const valid = rows.filter((r) => r.valid === true);
  const drawTable = () => {
    const sorted = [...valid].sort((a, b) => (a[sortCol] - b[sortCol]) * sortDir);
    const head = h('tr', {}, h('th', {}, ''), TABLE_COLUMNS.map((c) => h('th', {
      class: c === sortCol ? (sortDir > 0 ? 'sorted-asc' : 'sorted-desc') : null,
      onclick: () => { if (sortCol === c) sortDir = -sortDir; else { sortCol = c; sortDir = 1; } drawTable(); },
    }, c)));
    const body = sorted.map((r) => {
      const box = h('input', { type: 'checkbox', checked: selectedRows.has(r.id) });
      const tr = h('tr', { class: selectedRows.has(r.id) ? 'selected' : null }, h('td', {}, box),
        TABLE_COLUMNS.map((c) => h('td', {}, c === 'id' ? r[c] : Number(r[c]).toFixed(4))));
      box.addEventListener('change', () => {
        if (box.checked) selectedRows.add(r.id); else selectedRows.delete(r.id);
        tr.classList.toggle('selected', box.checked);
        drawBars();
      });
      return tr;
    });
    tableBox.replaceChildren(h('div', { class: 'results-table-wrap' },
      h('table', { class: 'results-table' }, h('thead', {}, head), h('tbody', {}, body))));
  };

  const exportLink = h('a', { href: '#', onclick: (e) => { e.preventDefault(); download('optimizationresistance.csv', resultsToCsv(rows)); } },
    'Export all individuals generated');

  root.append(h('div', { class: 'container mt-4' },
    h('div', { class: 'row' }, h('div', { class: 'col' }, h('h4', {}, 'Results'))),
    !state.results ? h('div', { class: 'alert alert-info py-2' }, 'These are the results of an example optimization. Run your own on the Optimization tab.') : null,
    h('div', { class: 'row' },
      h('div', { class: 'col-md justify' }, h('p', {}, "The main results are displayed below. First, you can view the evolutionary process in the first main plot. Colors will indicate how the individual evolved towards the optimal solution after each new generation. When hovering each individual, you can see the plot of each resistance component updating, as well a representation of the hull sections. The data includes also individuals that are not valid, and the constraints disrespected can be seen in the 'Constraints' menu below. The same plot also allows visualizing and understanding the Pareto frontier, in which further improvement is not possible.")),
      h('div', { class: 'col-md justify' }, h('p', {}, 'Besides that, a list with all the individuals generated is displayed in a comprehensive dynamic table. In this table, the user can sort the values combining ascending and descending sorting in each column. Another import asset is the parallel dimensions plot. It shows how the dimension set of the hull throughout the optimization process. The concentration at one of the extremes may indicate space for further exploration and also a trend to what values give the best results.'))),
    exportLink, h('br'), h('br'),
    h('div', { class: 'row' }, h('div', { class: 'col' }, h('h5', {}, 'What do you want to view?'))),
    h('div', { class: 'row align-items-center' },
      h('div', { class: 'col' }, select('resultshullaxisy', AXES, state.axes.y, (v) => { state.axes.y = v; saveState(); drawMain(); })),
      h('div', { class: 'col-auto' }, h('p', { class: 'm-0' }, 'versus')),
      h('div', { class: 'col' }, select('resultshullaxisx', AXES, state.axes.x, (v) => { state.axes.x = v; saveState(); drawMain(); }))),
    h('br'),
    h('div', { class: 'row' },
      h('div', { class: 'col-md-10' }, main,
        h('h4', {}, 'Select one individual'),
        h('p', {}, 'Among all the individuals generated throughout the optimization proccess, select one by hovering over it (or clicking it) in the plot above. The table below and the Pareto Frontier will help you to find the specific hull number, equivalent to the individual ID, that fits your needs. The selected hull is used on the Appendages tab.'),
        chosen),
      h('div', { class: 'col-md-2' }, bar)),
    h('details', {}, h('summary', {}, 'Data of all individuals'), h('br'),
      h('p', {}, 'All the valid individuals are listed below. By reordering the columns, the hulls with least resistance or displacement can be found. When selected, the following plots will be automatically update ith their position in the optimization course.'),
      tableBox, h('br'), barsBox)));

  drawMain();
  choose(state.selectedId || 1);
  drawTable();
  root.querySelector('details').addEventListener('toggle', function once(e) {
    if (e.target.open) { drawBars(); e.target.removeEventListener('toggle', once); }
  });
}

/* --------------------------------------------------------- tab: appendages */

const SECTION_DEPS = {
  'lwl-new': ['sail', 'rudder', 'keel'],
  'disp-new': ['sail', 'rudder', 'keel'],
  'tc-new': ['keel'],
  'bwl-new': ['boa'],
  'sailset': ['sail'],
  'mzn-check': ['mizzen'],
  'bulbo-check': ['bulb'],
};
const ALL_SECTIONS = ['boa', 'sail', 'rudder', 'keel', 'mizzen', 'bulb'];

function renderAppendages(root) {
  const hull = state.selectedHull;
  const hullKey = JSON.stringify(hull);
  if (!state.appendages || state.appendages.hullKey !== hullKey) {
    // a new hull was selected: start from its dimensions and the default values
    // same text as Python's format(round(x, 2)): 10.0, 3.17, 9.86
    const f = (x) => { const r = Math.round(Number(x) * 100) / 100; return Number.isInteger(r) ? r.toFixed(1) : String(r); };
    state.appendages = {
      hullKey,
      values: {
        'lwl-new': f(hull.lwl), 'bwl-new': f(hull.bwl), 'tc-new': f(hull.tc), 'disp-new': f(hull.disp),
        'lcb-new': f(hull.lcb), 'lcf-new': f(hull.lcf),
        freeboard: '1.3', overhang: '1', bowangle: '15', sailset: '1', 'mzn-check': '0',
        crewmass: '280', 'ballast-ratio': '28', 'keel-naca': '1', 'rudder-naca': '1', 'bulbo-check': '0',
      },
      fieldsReady: false,
    };
  }
  const v = state.appendages.values;
  if (v['show-dimensions'] === undefined) v['show-dimensions'] = '1';
  const P = state.appendages.polar || (state.appendages.polar = { wind: [6, 20], kg: '0.8' });
  const sectionBoxes = Object.fromEntries(ALL_SECTIONS.map((s) => [s, h('div', { id: 'dimensions-' + s })]));
  const plot = graph('plot-appendages', 800);
  const loaBox = h('div', { id: 'dimension-loa' });
  const areaBox = h('div', { id: 'dimension-area', style: { width: '50%' } });

  const redraw = debounce(() => {
    if (!Object.entries(v).every(([, x]) => isNumber(x))) return;
    Engine.callLatest('appview', 'appendages.view', { values: v }).then((r) => {
      drawFigure(plot, r.figure);
      clearGraphError(plot);
      loaBox.replaceChildren(h('p', {}, r.summary.loa_text), simpleTable(r.summary.stability));
      areaBox.replaceChildren(simpleTable(r.summary.areas));
    }, (err) => showGraphError(plot, err));
  }, 200);

  const changed = (key, value) => {
    v[key] = value;
    saveState();
    markPolarOutdated();
    // like the Dash callbacks: changing a hull dimension or an option recomputes
    // the default sizes of the parts that depend on it
    const deps = SECTION_DEPS[key];
    const hullOk = ['lwl-new', 'disp-new', 'tc-new', 'bwl-new'].every((k) => isNumber(v[k]));
    if (deps && hullOk) regenerate(deps);
    else redraw();
  };

  const field = (id, label) => [h('label', { for: id }, label), textInput(id, v[id], (x) => changed(id, x), 'boxinput')];
  const fullField = (id, label) => [h('label', { for: id }, label), textInput(id, v[id], (x) => changed(id, x))];

  function drawSection(name, fields) {
    const wide = name === 'mizzen' || name === 'bulb';
    sectionBoxes[name].replaceChildren(...fields.map(([id, label, value]) => {
      v[id] = value;
      return (wide ? fullField : field)(id, label);
    }).flat());
  }

  function regenerate(sections) {
    return Engine.callLatest('fields-' + sections.join(), 'appendages.fields', { sections, values: v }).then((out) => {
      for (const [name, fields] of Object.entries(out)) drawSection(name, fields);
      state.appendages.fieldsReady = true;
      saveState();
      redraw();
    }, (err) => showGraphError(plot, err));
  }

  /* polar diagram (Velocity Prediction Program) */
  const polarPlot = graph('polar-diagram', 560);
  const polarStatus = h('div', { class: 'small text-muted mt-1', id: 'polar-status' });
  const polarButton = h('button', { type: 'button', id: 'polar-button', class: 'btn btn-outline-dark btn-sm' }, 'Calculate polar diagram');
  let polarRunning = false;
  let polarDrawn = false;

  function markPolarOutdated() {
    if (polarDrawn && !polarRunning) polarStatus.textContent = 'The inputs changed: press "Calculate polar diagram" to update it.';
  }

  async function runPolar() {
    if (polarRunning || !polarButton.isConnected) return;
    if (!Object.values(v).every(isNumber) || !isNumber(P.kg)) {
      polarStatus.textContent = 'Please check the inputs: every box needs a number.';
      return;
    }
    polarRunning = true;
    polarButton.disabled = true;
    polarButton.textContent = 'Calculating…';
    polarStatus.textContent = 'Solving the VPP…';
    const t0 = performance.now();
    const vpp = getVppEngine();
    vpp.onProgress((done, total) => { polarStatus.textContent = `Solving the VPP: true wind speed ${done + 1} of ${total}…`; });
    try {
      const r = await vpp.call('appendages.polar', { values: { ...v }, wind_min: P.wind[0], wind_max: P.wind[1], kg: P.kg });
      drawFigure(polarPlot, r.figure);
      clearGraphError(polarPlot);
      polarDrawn = true;
      polarStatus.textContent = `${r.converged} of ${r.total} wind conditions converged (${((performance.now() - t0) / 1000).toFixed(1)} s). ` +
        'Gaps in the curves are conditions where the VPP found no equilibrium, mostly close to dead downwind.';
    } catch (err) {
      showGraphError(polarPlot, err);
      polarStatus.textContent = '';
    } finally {
      vpp.onProgress(null);
      polarRunning = false;
      polarButton.disabled = false;
      polarButton.textContent = 'Calculate polar diagram';
    }
  }
  polarButton.addEventListener('click', runPolar);

  const polarSection = h('div', { class: 'mt-4', id: 'polar-section' },
    h('h5', {}, 'Polar diagram'),
    h('p', { class: 'justify' }, 'Boat speed predicted by the Velocity Prediction Program (VPP) for the dimensions on this page. For every true wind speed and angle, the VPP looks for the speed, leeway, heel and rudder angle at which the aerodynamic and hydrodynamic forces and moments balance (surge, sway, roll and yaw).'),
    h('div', { class: 'row align-items-end' },
      h('div', { class: 'col-sm-8' },
        h('label', {}, 'True wind speeds [kn]'),
        slider({ id: 'polar-wind', min: 4, max: 24, step: 2, start: P.wind, label: (x) => `${x[0]} to ${x[1]} kn, every 2 kn`,
          marks: { 4: '4', 8: '8', 12: '12', 16: '16', 20: '20', 24: '24' },
          onChange: (x) => { P.wind = x; saveState(); markPolarOutdated(); } })),
      h('div', { class: 'col-sm-4' },
        h('label', { for: 'polar-kg' }, 'Centre of gravity KG [m]'),
        textInput('polar-kg', P.kg, (x) => { P.kg = x; saveState(); markPolarOutdated(); }))),
    polarButton, polarStatus,
    polarPlot);

  const dimsToggle = h('div', { class: 'form-check form-switch' },
    h('input', { class: 'form-check-input', type: 'checkbox', id: 'show-dimensions', checked: v['show-dimensions'] === '1',
      onchange: (e) => { v['show-dimensions'] = e.target.checked ? '1' : '0'; saveState(); redraw(); } }),
    h('label', { class: 'form-check-label', for: 'show-dimensions' }, 'Show dimensions'));

  root.append(h('div', { class: 'container mt-4' },
    h('div', { class: 'row' }, h('div', { class: 'col' }, h('h4', {}, 'Dimensions'))),
    h('div', { class: 'row' },
      h('div', { class: 'col-md justify' },
        h('p', {}, 'After optimizing the the hull main dimensions, in this phase we will concentrate in stablishing the dimensions for the rudder, keel and sails in order to improve its overall performance. At this page, you have the dimensions of the hull you selected before. You can change them, but have in mind it can cause an unfeasible vessel or decrease its performance.'),
        h('p', {}, 'Below, you will find the dimensions necessary for running the VPP - Velocity Prediction Program. In order to ease the prelimnary setup, regressions based on the hull main dimensions were applied to estimated them. However, you are encouraged to investigate and adapt them to your needs. You can see how they affect the sailboat by looking at the dynamic profile on the right side. Bear in mind that they depend on one another.')),
      h('div', { class: 'col-md' }, h('div', { class: 'row' },
        h('div', { class: 'col' }, fullField('lwl-new', 'Waterline length [m]'), fullField('bwl-new', 'Waterline beam [m]'), fullField('tc-new', 'Draft [m]')),
        h('div', { class: 'col' }, fullField('disp-new', 'Displacement [m3]'), fullField('lcb-new', 'LCB [m]'), fullField('lcf-new', 'LCF [m]'))))),
    h('br'),
    h('div', { class: 'row' },
      h('div', { class: 'col-md-3' },
        h('h5', {}, 'Hull'),
        field('freeboard', 'Free Board [m]'),
        sectionBoxes.boa,
        field('overhang', 'Overhang [m]'),
        field('bowangle', 'Bow angle [deg]'),
        h('br'),
        h('h5', {}, 'Sail'),
        h('label', { for: 'sailset' }, 'Sail configuration'),
        select('sailset', [['1', 'Sloop: Mainsail and foresail'], ['2', 'Cat: Mainsail and spinnaker'],
          ['3', 'Cutter: Mainsail, foresail, and spinnaker'], ['4', 'Cat: Mainsail only']], v.sailset, (x) => changed('sailset', x)),
        sectionBoxes.sail,
        h('label', { for: 'mzn-check' }, 'Mizzen'),
        select('mzn-check', [['0', 'Do not include'], ['1', 'Include']], v['mzn-check'], (x) => changed('mzn-check', x)),
        sectionBoxes.mizzen),
      h('div', { class: 'col-md-3' },
        h('h5', {}, 'Rudder'), sectionBoxes.rudder, h('br'),
        h('h5', {}, 'Keel'), sectionBoxes.keel, h('br'),
        h('h5', {}, 'Extra data'),
        field('crewmass', 'Crew mass [kg]'),
        field('ballast-ratio', 'Ballast Ratio [%]'),
        h('label', { for: 'keel-naca' }, 'Keel Naca Profile'),
        select('keel-naca', [['1', '4 digits'], ['2', '6 digits']], v['keel-naca'], (x) => changed('keel-naca', x)),
        h('label', { for: 'rudder-naca' }, 'Rudder Naca Profile'),
        select('rudder-naca', [['1', '4 digits'], ['2', '6 digits']], v['rudder-naca'], (x) => changed('rudder-naca', x)),
        h('label', { for: 'bulbo-check' }, 'Bulb keel'),
        select('bulbo-check', [['0', 'Do not include'], ['1', 'Include']], v['bulbo-check'], (x) => changed('bulbo-check', x)),
        sectionBoxes.bulb),
      h('div', { class: 'col-md-6' },
        h('div', { class: 'd-flex justify-content-between align-items-center' }, h('h5', { class: 'mb-0' }, 'Side plan view'), dimsToggle),
        plot, h('br'),
        loaBox, h('br'),
        areaBox,
        polarSection))));

  if (state.appendages.fieldsReady) {
    // redraw the saved values without recomputing the defaults
    const known = {
      boa: [['boa', 'Beam [m]']],
      sail: [['psail', 'Mainsail hoist - P [m]'], ['esail', 'Mainsail foot - E [m]'], ['isail', 'Jib height - I [m]'], ['jsail', 'Jib base - J [m]'],
        ['lpg', 'Perpendicular of longest jib [m]'], ['spl', 'Spinnaker leech length [m]'], ['mast-diameter', 'Mast average diameter [m]'],
        ['boom-height', 'Height of main boom above sheer [m]'], ['mast-height', 'Mast height above sheerline [m]'], ['mastpos', 'Mast longitudinal position [m]']],
      rudder: [['rootchord-rudder', 'Root Chord'], ['tipchord-rudder', 'Tip chord'], ['span-rudder', 'Span'], ['sweep-rudder', 'Sweep angle [degrees]'],
        ['heightsurface-rudder', 'Height above or below waterline'], ['pos-rudder', 'Root Centerline'], ['rootchord-rudder-tcks', 'Root Chord Thickness'],
        ['tipchord-rudder-tcks', 'Tip Chord Thickness']],
      keel: [['rootchord-keel', 'Root Chord'], ['tipchord-keel', 'Tip Chord'], ['span-keel', 'Span'], ['sweep-keel', 'Sweep angle [degrees]'],
        ['pos-keel', 'Root Centerline'], ['rootchord-keel-tcks', 'Root Chord Thickness'], ['tipchord-keel-tcks', 'Tip Chord Thickness']],
      mizzen: [['pmz', 'Mizzen Hoist'], ['emz', 'Mizzen Foot'], ['badmz', 'Boom height']],
      bulb: [['lbk', 'Keel bulbous length'], ['abk', 'Keel bulbous lateral area'], ['sbk', 'Keel bulbous wetted area']],
    };
    for (const [name, fields] of Object.entries(known)) drawSection(name, fields.map(([id, label]) => [id, label, v[id]]));
    redraw();
    setTimeout(runPolar, 400);
  } else {
    regenerate(ALL_SECTIONS).then(() => setTimeout(runPolar, 400));
  }
}

/* ------------------------------------------------------------- tab: about */

function renderAbout(root) {
  const person = (photo, name, role, text) => h('div', { class: 'col-lg-8 mb-4' },
    h('div', { class: 'about-person' },
      photo,
      h('div', {}, h('h5', { class: 'mb-0' }, name), h('div', { class: 'about-role' }, role), h('p', { class: 'mt-2 mb-0' }, text))));
  const initials = (txt) => h('div', { class: 'about-initials' }, txt);
  // a photo that falls back to initials if the image file is not there
  const photoOr = (src, alt, txt) => {
    const img = h('img', { src, alt, class: 'about-photo' });
    img.addEventListener('error', () => img.replaceWith(initials(txt)));
    return img;
  };

  root.append(h('div', { class: 'container mt-4 about' },
    h('div', { class: 'row' }, h('div', { class: 'col-lg-8' },
      h('h4', {}, 'About SailPy'),
      h('p', { class: 'lead about-lead' }, 'An open-source tool for the preliminary design of sailing yachts: it explores hull dimensions with genetic algorithms, estimates resistance with the Delft Systematic Yacht Hull Series and predicts performance with a Velocity Prediction Program.'),
      h('p', { class: 'justify' }, "SailPy was developed as part of a Master's research project at the Department of Naval Architecture and Ocean Engineering of the Polytechnic School (Escola Politécnica) of the University of São Paulo. Its aim is to show how the main dimensions of the hull affect performance in calm water and in waves, and to help find better sets of dimensions early in the design."))),
    h('h5', { class: 'mt-3 mb-3' }, 'People'),
    h('div', { class: 'row' },
      person(photoOr('assets/static/diogo.png', 'Diogo Kramel', 'DK'), 'Diogo Kramel', 'Author and developer',
        "Degree in Naval Architecture and Ocean Engineering and Master of Science from the University of São Paulo (USP), and a Master's degree in Maritime Spatial Planning from the University of the Azores, the University of Seville and Università Iuav di Venezia."),
      person(photoOr('assets/static/alexandre.jpg', 'Alexandre Nicolaos Simos', 'AS'), 'Prof. Dr. Alexandre Nicolaos Simos', 'Supervisor',
        'Department of Naval Architecture and Ocean Engineering, Polytechnic School of the University of São Paulo.')),
    h('div', { class: 'row' },
      h('div', { class: 'col-lg-8' },
        h('h5', { class: 'mt-2' }, 'The research'),
        h('div', { class: 'about-thesis' },
          h('div', { class: 'about-thesis-title' }, 'Desenvolvimento de uma ferramenta para otimização paramétrica da resistência hidrodinâmica de veleiros através da série de Delft'),
          h('div', { class: 'text-muted small mb-2' }, 'Development of a tool for the parametric optimization of the hydrodynamic resistance of sailing yachts using the Delft series'),
          h('div', { class: 'small' }, "Master's dissertation (Mestrado em Ciências), Escola Politécnica, Universidade de São Paulo, 2021."),
          h('a', { href: 'assets/Thesis.pdf', target: '_blank', rel: 'noopener', class: 'btn btn-sm btn-outline-primary mt-2' }, 'Read the dissertation (PDF, Portuguese)')),
        h('p', { class: 'justify mt-3' }, 'The performance of sailing yachts is assessed with the Delft Systematic Yacht Hull Series, which estimates the hydrodynamic forces in calm water and in waves. These forces are coupled with genetic algorithms that search for alternative hull dimensions minimising the total hydrodynamic resistance, and the methodology is made available in this online tool.'),
        h('h5', { class: 'mt-4' }, 'Methods and credits'),
        h('ul', { class: 'about-list' },
          h('li', {}, 'Resistance in calm water and in waves: Delft Systematic Yacht Hull Series (Keuning and Sonnenberg, 1998; Keuning, Vermeulen and ten Have, 2006).'),
          h('li', {}, 'Optimization: multi-objective genetic algorithms (NSGA-II, GDE3, OMOPSO, SMPSO, SPEA2, ε-MOEA) from the Platypus library.'),
          h('li', {}, 'Appendages and sails: initial estimates from the regressions of Simos, Illuminati and Prado (2007).'),
          h('li', {}, 'Velocity Prediction Program: developed at the Department of Naval Architecture and Ocean Engineering of USP (Kantorowitz, 2019).'),
          h('li', {}, 'This work was supported by CAPES (Coordenação de Aperfeiçoamento de Pessoal de Nível Superior, Brazil), Finance Code 001.')),
        h('h5', { class: 'mt-4' }, 'How to cite'),
        h('p', { class: 'about-cite' }, 'KRAMEL, D. Desenvolvimento de uma ferramenta para otimização paramétrica da resistência hidrodinâmica de veleiros através da série de Delft. Dissertação (Mestrado), Escola Politécnica, Universidade de São Paulo, São Paulo, 2021.'),
        h('h5', { class: 'mt-4' }, 'Source code'),
        h('p', {}, 'SailPy is open source under the MIT license. Suggestions, bug reports and contributions are welcome on ',
          h('a', { href: 'https://github.com/DiogoKramel/SailPy', target: '_blank', rel: 'noopener' }, 'GitHub'), '.'),
        h('p', { class: 'small text-muted' }, 'This web version runs entirely in your browser: the Python code is executed locally with Pyodide, so nothing you enter is sent to a server.')))));
}

/* ----------------------------------------------------------------- router */

const TABS = {
  introduction: renderIntroduction,
  hull: renderHull,
  optimization: renderOptimization,
  results: renderResults,
  appendages: renderAppendages,
  about: renderAbout,
};

function route() {
  const hash = location.hash.replace(/^#/, '');
  const onApp = hash.startsWith('application');
  document.body.classList.toggle('on-landing', !onApp);
  $('#landing').hidden = onApp;
  $('#application').hidden = !onApp;
  if (!onApp) return;

  const tab = TABS[hash.split('/')[1]] ? hash.split('/')[1] : 'introduction';
  document.querySelectorAll('#tabs .nav-link').forEach((a) => a.classList.toggle('active', a.dataset.tab === tab));
  const content = $('#page-content');
  content.querySelectorAll('.js-plotly-plot').forEach((el) => Plotly.purge(el));
  content.replaceChildren();
  TABS[tab](content);
  if (tab === 'optimization' && lastOptimizationMessage) {
    $('#output-button').replaceChildren(lastOptimizationMessage);
    lastOptimizationMessage = null;
  }
  window.scrollTo(0, 0);
}

window.addEventListener('hashchange', route);

$('#reset-link').addEventListener('click', (e) => {
  e.preventDefault();
  if (!confirm('Clear everything saved in this browser (hull, optimization results, appendages) and start again?')) return;
  try { localStorage.removeItem(STORAGE_KEY); } catch (err) { /* ignore */ }
  state = structuredClone(DEFAULT_STATE);
  location.hash = '#application/introduction';
  route();
});

$('[data-engine-status]').textContent = 'Preparing the Python engine in the background (about 13 MB on the first visit)…';

fetch('data/optimizationresistance.csv').then((r) => r.text()).then((text) => {
  exampleResults = { rows: parseResultsCsv(text), gamethod: 'NSGAII' };
  if (location.hash.includes('results') && !state.results) route();
});

route();