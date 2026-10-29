"""Entry point used by the browser (js/engine-worker.js).

call('module.function', '{"arg": ...}') runs one of the functions in this
package with keyword arguments given as JSON and returns the result as JSON.
"""
import json
import math

from . import appendages, hull, optimization, results

MODULES = {'hull': hull, 'optimization': optimization, 'results': results, 'appendages': appendages}

_progress = None
_rows = None   # results of the last optimization (or the example run)


def set_progress(callback):
    global _progress
    _progress = callback


def _clean(obj):
    if isinstance(obj, float):
        return obj if math.isfinite(obj) else None
    if isinstance(obj, dict):
        return {k: _clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_clean(v) for v in obj]
    return obj


def call(name, args_json):
    """Run ``module.function`` with JSON keyword arguments; return JSON.

    The individuals of the current optimization are kept here between calls,
    so the page can pass rows="current" instead of sending them every time.
    """
    global _rows
    kwargs = json.loads(args_json) if args_json else {}
    if name == 'rows.set':
        _rows = kwargs['rows']
        return json.dumps(len(_rows))
    if kwargs.get('rows') == 'current':
        kwargs['rows'] = _rows
    module_name, func_name = name.split('.')
    func = getattr(MODULES[module_name], func_name)
    if name in ('optimization.run', 'appendages.polar'):
        kwargs['progress'] = _progress
    result = func(**kwargs)
    if name == 'optimization.run':
        _rows = result['rows']
    return json.dumps(_clean(result))
