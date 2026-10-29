"""Optimization Results tab (from callbacks/resultshullplots.py).

``rows`` is the list of individuals produced by optimization.run() (the same
columns as optimizationresistance.csv in the Dash version).
"""
from . import go


def _col(rows, name):
    return [r[name] for r in rows]


def pareto_frontier(Xs, Ys, maxX=True, maxY=True):
    myList = sorted([[Xs[i], Ys[i]] for i in range(len(Xs))], reverse=maxX)
    p_front = [myList[0]]
    for pair in myList[1:]:
        if maxY:
            if pair[1] >= p_front[-1][1]:
                p_front.append(pair)
        else:
            if pair[1] <= p_front[-1][1]:
                p_front.append(pair)
    p_frontX = [pair[0] for pair in p_front]
    p_frontY = [pair[1] for pair in p_front]
    return p_frontX, p_frontY


def scatter(rows, resultshullaxisy, resultshullaxisx, gamethod):
    df = rows
    dfvalid = [r for r in rows if r['valid'] is True]
    dfnotvalid = [r for r in rows if r['valid'] is False]

    if dfvalid:
        p_front = pareto_frontier(_col(dfvalid, "Comfort"), _col(dfvalid, "Resistance"), maxX=True, maxY=False)
    else:
        p_front = ([], [])
    if (resultshullaxisx == "Comfort" and resultshullaxisy == "Resistance"):
        paretox, paretoy, paretoname = p_front[0], p_front[1], 'Pareto'
    elif (resultshullaxisx == "Resistance" and resultshullaxisy == "Comfort"):
        paretoy, paretox, paretoname = p_front[0], p_front[1], 'Pareto'
    else:
        paretoy, paretox, paretoname = [], [], 'No Pareto'

    ymin = min(_col(df, resultshullaxisy))*0.9
    ymax = max(_col(df, resultshullaxisy))
    if ymax > 7000:
        ymax = 7000

    ids = _col(df, "id")
    max_id = max(ids)
    # the original coloured the valid points with the colours of *all* rows;
    # use each valid individual's own id so colour = generation
    valid_ids = _col(dfvalid, "id")
    return go.figure(
        [
            go.Scatter(
                x=_col(dfvalid, resultshullaxisx),
                y=_col(dfvalid, resultshullaxisy),
                text=valid_ids,
                customdata=valid_ids,
                mode='markers',
                name='Valid individuals',
                marker=dict(
                    cmax=max_id, cmin=1, color=valid_ids,
                    colorbar=dict(title='#Offspring'),
                    colorscale='Viridis',
                    opacity=[0.5+0.5*i/max_id for i in valid_ids],
                ),
            ),
            go.Scatter(
                x=_col(dfnotvalid, resultshullaxisx),
                y=_col(dfnotvalid, resultshullaxisy),
                text=_col(dfnotvalid, "id"),
                customdata=_col(dfnotvalid, "id"),
                mode='markers',
                name='Invalid',
                marker=dict(color='rgba(255,0,0,0.2)', symbol='cross'),
            ),
            go.Scatter(
                x=[df[0][resultshullaxisx]],
                y=[df[0][resultshullaxisy]],
                text=[df[0]["id"]],
                customdata=[df[0]["id"]],
                mode='markers',
                name='Initial hull',
                marker=dict(symbol='star', size=10, color="black"),
            ),
            go.Scatter(x=paretox, y=paretoy, mode='lines', name=paretoname, line=dict(dash='dash'), hoverinfo='skip'),
        ],
        go.Layout(
            title="{} Optimization".format(gamethod),
            height=500,
            hovermode="closest",
            margin={"r": 20, "t": 30, "b": 50, "l": 80},
            xaxis={"autorange": True, "linewidth": 1, "showgrid": True, "showline": True, "mirror": True,
                   "title": resultshullaxisx},
            yaxis={"autorange": False, "linewidth": 1, "showgrid": True, "showline": True, "mirror": True,
                   "title": resultshullaxisy, "range": [ymin, ymax]},
            legend=dict(x=0.75, y=1),
            font=dict(size=12),
        ),
    )


def _find(rows, hover):
    for r in rows:
        if r['id'] == hover:
            return r
    return rows[0]


def resistance_bar(rows, hover=1):
    row = _find(rows, int(hover))
    hover = row['id']
    return go.figure(
        [
            go.Bar(x=['R'], y=[row['Rv']], name="Viscous", marker=dict(color='rgb(43,140,190)')),
            go.Bar(x=['R'], y=[row['Ri']], name="Induced", marker=dict(color='rgb(123,204,196)')),
            go.Bar(x=['R'], y=[row['Rr']], name="Residual", marker=dict(color='rgb(186,228,188)')),
            go.Bar(x=['R'], y=[row['Rincli']], name="Inclination", marker=dict(color='rgb(240,249,232)')),
        ],
        go.Layout(
            barmode="stack",
            title="Resistance #{}".format(hover),
            hovermode="closest",
            height=600,
            margin={"r": 20, "t": 30, "b": 50, "l": 50},
            yaxis={"title": "Resistance Components"},
            legend=dict(x=-.1, y=-0.3),
            font=dict(size=10),
        ),
    )


def selected_hull(rows, index=1):
    """The individual chosen on the results plot; becomes the hull used on the
    Appendages tab (dimensions-hull.json in the Dash version)."""
    row = _find(rows, int(index))
    hull = {'lwl': float(row['LWL']), 'bwl': float(row['BWL']), 'tc': float(row['Draft']),
            'disp': float(row['Displacement']), 'lcb': float(row['LCB']), 'lcf': float(row['LCF'])}
    text = [
        "Capsize Screening Factor: {}".format(round(float(row['CS']), 2)),
        "Waterline Length: {}m -- Waterline Beam: {}m -- Draft: {}m".format(round(hull['lwl'], 2), round(hull['bwl'], 2), round(hull['tc'], 2)),
    ]
    return {'id': row['id'], 'hull': hull, 'text': text}


def dimension_bars(rows, selected_ids):
    """Small bar charts under the table; the selected individuals are shown in green."""
    datatable_valid = [r for r in rows if r['valid'] is True]
    datatable_unvalid = [r for r in rows if r['valid'] is False]
    selected = [r for r in rows if r['id'] in set(selected_ids or [])]
    xmax = len(rows)
    figures = []
    for column in ["LWL", "BWL", "Draft", "Resistance", "Comfort"]:
        figures.append(go.figure(
            [
                go.Bar(x=_col(datatable_valid, "id"), y=_col(datatable_valid, column), name='Valid'),
                go.Bar(x=_col(datatable_unvalid, "id"), y=_col(datatable_unvalid, column), marker=dict(color='red'), name='Not valid'),
                go.Bar(x=_col(selected, "id"), y=_col(selected, column), marker=dict(color='green'), name='Selected'),
            ],
            {
                "xaxis": {"automargin": False, "range": [0, xmax]},
                "yaxis": {"automargin": True},
                "height": 120,
                "margin": {"t": 30, "l": 40, "r": 10, "b": 20},
                "title": column,
                'font': dict(size=9),
                'barmode': 'overlay',
            },
        ))
    return figures
