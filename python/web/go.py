"""A tiny stand-in for plotly.graph_objs.

The figures are drawn by Plotly.js in the browser, so the Python side only has
to produce plain dicts. Keeping the go.Scatter / go.Bar / go.Layout spelling
means the figure code reads exactly like the original Dash callbacks.
"""


def Scatter(**kwargs):
    return dict(type='scatter', **kwargs)


def Bar(**kwargs):
    return dict(type='bar', **kwargs)


def Layout(**kwargs):
    return dict(**kwargs)


def figure(data, layout):
    """Return a Plotly.js-ready figure (titles given as plain strings become
    {'text': ...}, the form Plotly.js 3 expects)."""
    return _fix_titles({'data': data, 'layout': layout})


def _fix_titles(obj):
    if isinstance(obj, dict):
        out = {}
        for key, value in obj.items():
            if key == 'title' and isinstance(value, str):
                out[key] = {'text': value}
            else:
                out[key] = _fix_titles(value)
        return out
    if isinstance(obj, (list, tuple)):
        return [_fix_titles(v) for v in obj]
    return obj
