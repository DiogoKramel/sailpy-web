# Third-party files

Everything the page needs is in this folder, so the site works without any CDN.

| Folder | What | Version | License |
|---|---|---|---|
| `pyodide/` | Pyodide: CPython compiled to WebAssembly (core runtime only: `pyodide.mjs`, `pyodide.asm.mjs`, `pyodide.asm.wasm`, `python_stdlib.zip`, `pyodide-lock.json`) | 314.0.7 (Python 3.14.2), from the `pyodide` npm package | MPL-2.0, https://github.com/pyodide/pyodide |
| `plotly/` | Plotly.js charts | 3.7.0 | MIT |
| `nouislider/` | Sliders | 15.8.1 | MIT |
| `bootstrap/` | Bootstrap 5 with the Bootswatch "Cosmo" theme (Google Fonts `@import` removed) | Bootswatch 5.3.6 | MIT |
| `source-sans-pro/` | Source Sans Pro font (latin, 300/400/700) | @fontsource 5.3.0 | SIL OFL 1.1 |
| `et-line-font/` | ET-Line icon font (from the original SailPy) | | as in the original repository |

`../python/vendor/Platypus_Opt-1.4.1-py3-none-any.whl` is the Platypus multi-objective
optimization library (GPL-3.0, https://github.com/Project-Platypus/Platypus), loaded into
Pyodide as-is.

To update Pyodide: `npm pack pyodide@<version>`, copy the five files listed above into
`pyodide/`. The Python code only uses the standard library plus Platypus, so no other
Pyodide packages are needed.
