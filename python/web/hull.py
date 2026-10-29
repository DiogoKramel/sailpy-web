"""Hull Dimensions tab (from callbacks/dimensionshullcall.py)."""
from functions.resistance import resistance
from . import go


def resistance_comparison(lwl, lwl2, bwl, bwl2, tc, tc2, cm, cm2, cp, cp2, cwp, cwp2, lcb, lcb2, lcf, lcf2, disp, disp2):
    froude_number = [0.2, 0.25, 0.3, 0.35, 0.4, 0.45]
    resistance1_tot = [0, 0, 0, 0, 0, 0]
    resistance1_visc = [0, 0, 0, 0, 0, 0]
    resistance1_res = [0, 0, 0, 0, 0, 0]
    resistance2_tot = [0, 0, 0, 0, 0, 0]
    resistance2_visc = [0, 0, 0, 0, 0, 0]
    resistance2_res = [0, 0, 0, 0, 0, 0]

    # NOTE: argument order kept exactly as in the original Dash app
    # (cm and cp are passed in the cp, cm positions of resistance()).
    for i in [0, 1, 2, 3, 4, 5]:
        resistance1 = resistance(float(lwl), float(bwl), float(tc), float(cm), float(cp), float(cwp), float(disp), float(lcb), float(lcf), froude_number[i]*(float(lwl)*9.81)**0.5, 0)
        resistance2 = resistance(float(lwl2), float(bwl2), float(tc2), float(cm2), float(cp2), float(cwp2), float(disp2), float(lcb2), float(lcf2), froude_number[i]*(float(lwl2)*9.81)**0.5, 0)
        resistance1_tot[i] = resistance1[0]
        resistance1_visc[i] = resistance1[1]
        resistance1_res[i] = resistance1[2]
        resistance2_tot[i] = resistance2[0]
        resistance2_visc[i] = resistance2[1]
        resistance2_res[i] = resistance2[2]

    # what the Dash version saved to dimensions.json (input to the optimization)
    dimensions = {'lwl': lwl, 'disp': disp, 'cwp': cwp, 'lcf': lcf, 'lcb': lcb, 'tc': tc, 'cm': cm, 'cp': cp, 'bwl': bwl}

    fig = go.figure(
        [
            go.Scatter(x=froude_number, y=resistance1_tot, name='Total - Boat #1',
                       marker=dict(color="rgb(128,0,38)"), line=dict(color="rgb(128,0,38)")),
            go.Scatter(x=froude_number, y=resistance2_tot, name='Total - Boat #2',
                       marker=dict(color="rgb(8,29,88)"), line=dict(color="rgb(8,29,88)")),
            go.Scatter(x=froude_number, y=resistance1_res, name='Residual - Boat #1',
                       marker=dict(color="rgb(227,26,28)"), line=dict(dash='dash', color="rgb(227,26,28)")),
            go.Scatter(x=froude_number, y=resistance2_res, name='Residual - Boat #2',
                       marker=dict(color="rgb(34,94,168)"), line=dict(dash='dash', color="rgb(34,94,168)")),
            go.Scatter(x=froude_number, y=resistance1_visc, name='Viscous - Boat #1',
                       marker=dict(color="rgb(253,141,60)"), line=dict(dash='dot', color="rgb(253,141,60)")),
            go.Scatter(x=froude_number, y=resistance2_visc, name='Viscous - Boat #2',
                       marker=dict(color="rgb(65,182,196)"), line=dict(dash='dot', color="rgb(65,182,196)")),
        ],
        go.Layout(
            height=500,
            hovermode="closest",
            margin={"r": 20, "t": 30, "b": 50, "l": 80},
            xaxis={"autorange": True, "linewidth": 1, "showgrid": True, "showline": True, "mirror": True,
                   "title": "Froude number"},
            yaxis={"autorange": False, "linewidth": 1, "showgrid": True, "showline": True, "mirror": True,
                   "title": "Resitance [N]",
                   "range": [0, max(max(resistance1), max(resistance2))*1.1]},
            legend=dict(x=0.0, y=1),
            font=dict(size=12),
        ),
    )
    return {'figure': fig, 'dimensions': dimensions}
