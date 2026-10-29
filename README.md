# SailPy (web version)

**SailPy** is a preliminary design tool for sailboats: it optimizes the main
dimensions of the hull with genetic algorithms and helps size the keel, rudder
and sails. It was developed by Diogo Kramel as his Master's thesis at the
Polytechnic School of the University of São Paulo.

This is the static version of the app. It needs **no server**: the original
Python code runs inside the visitor's browser with
[Pyodide](https://pyodide.org) (Python compiled to WebAssembly), so it can be
hosted for free on GitHub Pages, with your own domain if you like.

## How it works

```
index.html            the page
css/  js/             layout and interaction (js/app.js); js/engine-worker.js starts Python
python/functions/     the physics from the original app: resistance.py, resistance_added.py and vpp.py
                      (plus npcompat.py and minpack.py, pure-Python stand-ins for numpy/scipy)
python/web/           one module per tab, ported from the Dash callbacks (they return the charts)
python/vendor/        the Platypus optimization library
data/                 an example optimization shown before you run your own
assets/               images and the thesis PDF
vendor/               Pyodide, Plotly.js, Bootstrap, fonts (see vendor/README.md)
```

* When the page opens, a background worker downloads Python (about 13 MB the
  first time, cached by the browser afterwards) and loads the files in `python/`.
* Every calculation runs on the visitor's own computer. A 300-offspring
  optimization takes a couple of seconds and the page stays usable meanwhile.
* Each visitor's work (hull, optimization results, appendages) is saved in their
  own browser, so it survives a reload. "Start over" in the top bar clears it.

The Python code is the same as the Dash version's: in the physics files only the import
lines changed. They point to `python/functions/npcompat.py` (pure-Python stand-ins for the
numpy calls used) and `python/functions/minpack.py` (a port of MINPACK `hybrd`, the solver
behind `scipy.optimize.root` that the VPP uses), which keeps the download small. Checks
against the original:

* with the same random seed, the optimization produces exactly the same individuals;
* the VPP converges for exactly the same wind conditions and gives the same boat speeds
  (to 1e-11) as the numpy/scipy version, and runs about 8 times faster.

## Publish it on GitHub Pages (free)

1. Create a new repository on GitHub (for example `sailpy-web`), or use an existing one.
2. Upload the contents of this folder to it, keeping the folder structure. With git:
   ```
   cd sailpy-web
   git init
   git add .
   git commit -m "SailPy web version"
   git branch -M main
   git remote add origin https://github.com/<your-user>/<your-repo>.git
   git push -u origin main
   ```
   (or drag the files into **Add file → Upload files** on the repository page).
   (`.nojekyll` is a hidden, empty file that switches off GitHub's Jekyll
   processing; it is optional - the site works without it.)
3. In the repository go to **Settings → Pages**, choose **Deploy from a branch**,
   branch `main`, folder `/ (root)`, and save.
4. After a minute or two the site is live at
   `https://<your-user>.github.io/<your-repo>/`.

Any later change you push is published automatically.

## Use your own domain

1. Buy a domain (for example at Cloudflare, Porkbun or Namecheap).
2. In **Settings → Pages → Custom domain**, enter it (for example `sailpy.yourname.com`)
   and save.
3. At your domain registrar, add the DNS record:
   * for a subdomain such as `sailpy.yourname.com`: a **CNAME** record named `sailpy`
     pointing to `<your-user>.github.io`
   * for the bare domain `yourname.com`: four **A** records pointing to
     `185.199.108.153`, `185.199.109.153`, `185.199.110.153` and `185.199.111.153`
4. When GitHub shows the domain as verified, tick **Enforce HTTPS**.

## Run it on your computer

The page has to be served over http (opening `index.html` directly will not start
Python). From this folder:

```
python -m http.server 8000
```

and open http://localhost:8000.

## Changing the Python code

* Edit the files in `python/` and reload the page.
* If you add a new Python file, add its path to `PY_FILES` at the top of
  `js/engine-worker.js` so it is loaded into the browser.
* The modules in `python/web/` can also be imported and tested with normal Python
  (`pip install Platypus-Opt`, then run Python from the `python/` folder).

## Differences from the Dash version

New in the web version:

* **Polar diagram** on the Appendages tab, from the VPP (`functions/vpp.py`) with the values
  on that page (true wind speeds and KG can be set; wind angles 30-180 degrees every 5 degrees).
  It runs in its own background worker, so the page stays responsive. The form coefficients
  it needs (Cm 0.70, Cp 0.58, Cwp 0.75) are the Hull tab defaults; LCB and LCF are converted to
  the VPP's midship reference; the lever arms between the centres of effort come from the
  side plan view. Wind conditions where the VPP finds no equilibrium (mostly near dead
  downwind) are left as gaps.
* **Dimension lines** on the side plan view (LOA, LWL, P, E, I, J, BAD, EHM, keel and rudder
  spans, BOA, BWL, freeboard, canoe body draft and total draft), with a switch to hide them.
* **About** tab (project, people, dissertation, credits, how to cite).
* Two fixes in the VPP: the sail coefficients for spinnaker sail plans compared the whole
  array of wind angles instead of the current one (which crashed), and exactly 120 degrees
  is now handled consistently with the spinnaker area.

Other differences:

* The hidden `/saildata` page is not included (it was not linked from the app).
* The Appendages tab shows the hull selected on the results plot (in the Dash
  version it showed the hull from when the server started).
* On the results plot, the colour of each valid individual now matches its own
  offspring number, and the bar charts under the table highlight the rows you tick.
* Inputs and results are remembered in your browser between visits.

## Licensing

SailPy is licensed under MIT (see `LICENSE.md`). Third-party components keep their
own licenses (see `vendor/README.md`).
