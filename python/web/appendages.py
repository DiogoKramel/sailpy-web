"""Appendages, Sail and Polar diagram tab (from callbacks/dimensionsappendagescall.py
and callbacks/dimensionsappendagesplots.py).

The *_fields functions return the input boxes that the Dash callbacks created
(as (id, label, value) triples) so the page can draw them.
"""
import math

from . import go


def _f(x):
    return format(round(x, 2))


def boa_fields(bwlnew):
    boa = float(bwlnew)*1.3
    return [('boa', 'Beam [m]', _f(boa))]


def sail_fields(sailset, disp, lwl):
    lwl = float(lwl)
    ar = 2.95
    sa = 18*float(disp)**(2/3)
    sm = sa*0.6
    p = (2*sm*ar)**0.5
    e = 2*sm/p
    if sailset == "1" or sailset == "3":
        i = p*0.9
        j = 2*(sa-sm)/i
    else:  # "2" or "4"
        i = 0
        j = 0
    lpg = 1.5*j
    spl = 1.1*p
    mastheight = 1.2+float(p)+0.2
    mastpos = lwl*0.6
    return [
        ('psail', 'Mainsail hoist - P [m]', _f(p)),
        ('esail', 'Mainsail foot - E [m]', _f(e)),
        ('isail', 'Jib height - I [m]', _f(i)),
        ('jsail', 'Jib base - J [m]', _f(j)),
        ('lpg', 'Perpendicular of longest jib [m]', _f(lpg)),
        ('spl', 'Spinnaker leech length [m]', _f(spl)),
        ('mast-diameter', 'Mast average diameter [m]', _f(0.2)),
        ('boom-height', 'Height of main boom above sheer [m]', _f(1.2)),
        ('mast-height', 'Mast height above sheerline [m]', _f(mastheight)),
        ('mastpos', 'Mast longitudinal position [m]', _f(mastpos)),
    ]


def rudder_fields(lwl, disp):
    lwl = float(lwl)
    t = lwl/(0.19*lwl+4.0533)
    spanrudder = t*0.8
    sa = 18*float(disp)**(2/3)
    surfacerudder = 0.01*sa
    tiprudder = 0.7*surfacerudder/spanrudder
    rootrudder = 1.1*surfacerudder/spanrudder
    return [
        ('rootchord-rudder', 'Root Chord', _f(rootrudder)),
        ('tipchord-rudder', 'Tip chord', _f(tiprudder)),
        ('span-rudder', 'Span', _f(spanrudder)),
        ('sweep-rudder', 'Sweep angle [degrees]', _f(15)),
        ('heightsurface-rudder', 'Height above or below waterline', _f(-0.05)),
        ('pos-rudder', 'Root Centerline', _f(1)),
        ('rootchord-rudder-tcks', 'Root Chord Thickness', _f(0.175)),
        ('tipchord-rudder-tcks', 'Tip Chord Thickness', _f(0.105)),
    ]


def keel_fields(lwl, tc, disp):
    lwl = float(lwl)
    cekeel = lwl/2
    t = lwl/(0.19*lwl+4.0533)
    spankeel = t-float(tc)
    sa = 18*float(disp)**(2/3)
    surfacekeel = 0.03*sa
    tipkeel = 0.8*surfacekeel/spankeel
    rootkeel = 1.2*surfacekeel/spankeel
    return [
        ('rootchord-keel', 'Root Chord', _f(rootkeel)),
        ('tipchord-keel', 'Tip Chord', _f(tipkeel)),
        ('span-keel', 'Span', _f(spankeel)),
        ('sweep-keel', 'Sweep angle [degrees]', _f(35)),
        ('pos-keel', 'Root Centerline', _f(cekeel)),
        ('rootchord-keel-tcks', 'Root Chord Thickness', _f(0.175)),
        ('tipchord-keel-tcks', 'Tip Chord Thickness', _f(0.1)),
    ]


def mizzen_fields(mzncheck):
    if mzncheck == '1':
        return [('pmz', 'Mizzen Hoist', _f(4)), ('emz', 'Mizzen Foot', _f(2)), ('badmz', 'Boom height', _f(1))]
    return [('pmz', 'Mizzen Hoist', '0'), ('emz', 'Mizzen Foot', '0'), ('badmz', 'Boom height', '0')]


def bulb_fields(bulbocheck):
    if bulbocheck == '1':
        return [('lbk', 'Keel bulbous length', _f(1)), ('abk', 'Keel bulbous lateral area', _f(1)), ('sbk', 'Keel bulbous wetted area', _f(1))]
    return [('lbk', 'Keel bulbous length', '0'), ('abk', 'Keel bulbous lateral area', '0'), ('sbk', 'Keel bulbous wetted area', '0')]


class Dimensions:
    """Dimension lines (thin line, end ticks and a label) for the side plan."""
    COLOR = 'rgba(90, 90, 90, 0.85)'

    def __init__(self):
        self.shapes = []
        self.annotations = []

    def _line(self, x0, y0, x1, y1, dash=None):
        line = {'width': 0.8, 'color': self.COLOR}
        if dash:
            line['dash'] = dash
        self.shapes.append({'type': 'line', 'x0': x0, 'y0': y0, 'x1': x1, 'y1': y1, 'line': line, 'layer': 'above'})

    def h(self, x0, x1, y, name, value, label_below=True, tick=0.12):
        self._line(x0, y, x1, y)
        self._line(x0, y-tick, x0, y+tick)
        self._line(x1, y-tick, x1, y+tick)
        self.annotations.append(dict(x=(x0+x1)/2, y=y, text='{} {:.2f}'.format(name, value), showarrow=False,
                                     yshift=-8 if label_below else 8, font=dict(size=9, color='#444')))

    def v(self, x, y0, y1, name, value, tick=0.12, label_right=False):
        self._line(x, y0, x, y1)
        self._line(x-tick, y0, x+tick, y0)
        self._line(x-tick, y1, x+tick, y1)
        self.annotations.append(dict(x=x, y=(y0+y1)/2, text='{} {:.2f}'.format(name, value), showarrow=False,
                                     textangle=-90, xshift=8 if label_right else -8, font=dict(size=9, color='#444')))


def summary(v):
    """Overall length text and the two tables under the side plan view."""
    lwl, overhang, bowangle, freeboard = v['lwl-new'], v['overhang'], v['bowangle'], v['freeboard']
    disp, br, tc, bwl = v['disp-new'], v['ballast-ratio'], v['tc-new'], v['bwl-new']
    loa = float(lwl)+float(overhang)+math.tan(math.radians(float(bowangle)))*float(freeboard)
    loaft = loa/0.3048
    boa = float(bwl)*1.1
    dispmass = float(disp)*1025
    br = float(br)/100
    ssv = boa**2/(br*float(tc)*float(disp)**(1/3))
    avs = 110+(400/(ssv-10))
    cs = boa*3.28084/(dispmass*2.20462/64)**(1/3)
    cr = float(disp)*1025*2.20462/((boa*3.28084)**(4/3)*0.65*(0.7*float(lwl)*3.28084+0.3*loa*3.28084))

    arearudder = float(v['span-rudder'])*(float(v['rootchord-rudder'])+float(v['tipchord-rudder']))/2
    areakeel = float(v['span-keel'])*(float(v['rootchord-keel'])+float(v['tipchord-keel']))/2
    areasail = float(v['psail'])*float(v['esail'])/2+float(v['isail'])*float(v['jsail'])/2

    return {
        'loa_text': "The overall lenght of the vessel is {} feet, equivalent to {} meters.".format(float(round(loaft, 0)), round(loa, 2)),
        'stability': {
            'columns': ['Parameters', 'Values', 'Recommendation', 'Unit'],
            'rows': [['Angle of Vanishing Stability', round(avs, 2), '> 110', 'degrees'],
                     ['Capsize Screening Factor', round(cs, 2), '< 2', '-'],
                     ['Comfort Ratio', round(cr, 2), '> 30', '-']],
        },
        'areas': {
            'columns': ['Dimensions', 'Values', 'Unit'],
            'rows': [['Rudder Area', round(arearudder, 2), 'm2'],
                     ['Keel Area', round(areakeel, 2), 'm2'],
                     ['Sail Area', round(areasail, 2), 'm2']],
        },
    }


def side_plan(v):
    """Side plan view (the 'plot-appendages' figure)."""
    sailset = int(v['sailset'])
    lwl = float(v['lwl-new'])
    tc = float(v['tc-new'])
    bwl = float(v['bwl-new'])
    lcb = float(v['lcb-new'])
    lcf = float(v['lcf-new'])
    overhang = float(v['overhang'])
    bowangle = math.radians(float(v['bowangle']))
    freeboard = float(v['freeboard'])
    poskeel = float(v['pos-keel'])
    sweepkeel = math.radians(float(v['sweep-keel']))
    spankeel = float(v['span-keel'])
    tipchordkeel = float(v['tipchord-keel'])
    rootchordkeel = float(v['rootchord-keel'])
    heightsurfacerudder = float(v['heightsurface-rudder'])
    spanrudder = float(v['span-rudder'])
    rootchordrudder = float(v['rootchord-rudder'])
    tipchordrudder = float(v['tipchord-rudder'])
    sweeprudder = math.radians(float(v['sweep-rudder']))
    posrudder = float(v['pos-rudder'])
    mastdiameter = float(v['mast-diameter'])
    boomheight = float(v['boom-height'])
    boa = float(v['boa'])
    psail = float(v['psail'])
    esail = float(v['esail'])
    isail = float(v['isail'])
    jsail = float(v['jsail'])
    mastpos = float(v['mastpos'])
    rootchordkeeltcks = float(v['rootchord-keel-tcks'])
    tipchordkeeltcks = float(v['tipchord-keel-tcks'])
    rootchordruddertcks = float(v['rootchord-rudder-tcks'])
    tipchordruddertcks = float(v['tipchord-rudder-tcks'])
    pmz = float(v['pmz'])
    emz = float(v['emz'])
    badmz = float(v['badmz'])
    mzncheck = float(v['mzn-check'])

    deckx1 = -overhang
    decky1 = float(overhang)*(float(tc)/(float(lwl)/5))
    deckx2 = deckx1*0.9
    decky2 = freeboard*0.6
    deckx3 = 0
    decky3 = freeboard*0.9
    deckx4 = (math.tan(bowangle)*freeboard)+float(lwl)
    decky4 = freeboard*1.1
    deckx5 = lwl
    decky5 = 0
    cockpitx1 = lwl*0.3
    cockpity1 = freeboard*(0.9+0.2*cockpitx1/deckx4)
    cockpitx2 = lwl*0.35
    cockpity2 = freeboard*1.3
    cockpitx3 = lwl*0.65
    cockpity3 = freeboard*1.3
    cockpitx4 = lwl*0.8
    cockpity4 = freeboard*(0.9+0.2*cockpitx4/deckx4)
    keelx1 = poskeel+rootchordkeel/2
    keely1 = 0
    keelx2 = keelx1-math.tan(sweepkeel)*spankeel
    keely2 = -tc-spankeel
    keelx3 = keelx2-tipchordkeel
    keely3 = -tc-spankeel
    keelx4 = keelx1-rootchordkeel
    keely4 = 0
    rudderx1 = posrudder+rootchordrudder/2
    ruddery1 = heightsurfacerudder
    rudderx2 = rudderx1-math.tan(sweeprudder)*spanrudder
    ruddery2 = -spanrudder+heightsurfacerudder
    rudderx3 = rudderx2-tipchordrudder
    ruddery3 = -spanrudder+heightsurfacerudder
    rudderx4 = rudderx1-rootchordrudder
    ruddery4 = heightsurfacerudder
    mastdeflection = 0.15
    mastx1 = mastpos
    masty1 = freeboard*1.3
    mastx2 = mastpos+mastdiameter
    masty2 = freeboard*1.3
    mastx3 = mastpos+mastdiameter-mastdeflection
    masty3 = freeboard*1.3+boomheight+psail
    mastx4 = mastpos-mastdeflection
    masty4 = freeboard*1.3+boomheight+psail
    boomx1 = mastpos
    boomy1 = freeboard+boomheight-mastdiameter/2
    boomx2 = mastpos-esail
    boomy2 = freeboard+boomheight-mastdiameter/2
    boomx3 = mastpos-esail
    boomy3 = freeboard+boomheight+mastdiameter/2
    boomx4 = mastpos
    boomy4 = freeboard+boomheight+mastdiameter/2
    jibx1 = deckx4
    jiby1 = decky4
    jibx2 = deckx4-jsail
    jiby2 = freeboard+boomheight*0.5
    jibx3 = mastpos-mastdiameter/2
    jiby3 = freeboard+isail
    # centre of effort
    arearudder = spanrudder*(rootchordrudder+tipchordkeel)/2
    areakeel = spankeel*(rootchordkeel+tipchordkeel)/2
    areahull = lwl*tc*0.7
    b = rootchordkeel
    a = tipchordkeel
    cekeely = spankeel/3*((2*a+b)/(a+b))
    cekeelx = -(poskeel-(keelx2+keelx3)/2)/spankeel*cekeely
    d = rootchordkeel
    c = tipchordkeel
    ceruddery = spanrudder/3*((2*d+c)/(c+d))
    cerudderx = -(posrudder-(rudderx2+rudderx3)/2)/spanrudder*ceruddery
    cehidrox = ((cekeelx+poskeel)*areakeel+(cerudderx+posrudder)*arearudder+lwl/2*(areahull))/(areakeel+arearudder+areahull)
    cehidroy = (-(cekeely+tc)*areakeel-(ceruddery+heightsurfacerudder)*arearudder-tc*0.25*(areahull))/(areakeel+arearudder+areahull)

    mainarea = psail*esail/2
    if sailset == 1 or sailset == 3:
        jibarea = isail*jsail/2
        area = mainarea+jibarea
        cesailx = (mainarea*(-esail/3+mastpos)+jibarea*(deckx4-jsail*2/3))/(area)
        cesaily = (mainarea*(psail/3+boomheight+freeboard)+jibarea*(decky4+jsail/3))/(area)
    else:  # sailset 2 or 4
        cesailx = (-esail/3+mastpos)
        cesaily = (psail/3+boomheight+freeboard)

    jib = sailset == 1 or sailset == 3
    spinnaker = sailset == 2 or sailset == 3
    mizzen = mzncheck == 1

    shapes = [
        {  # cockpit
            'type': 'path',
            'path': ' M {},{} L {},{} L {},{} L {},{}'.format(cockpitx1, cockpity1, cockpitx2, cockpity2, cockpitx3, cockpity3, cockpitx4, cockpity4),
            'layer': 'above', 'line': {'width': 1},
        },
        {  # keel
            'type': 'path',
            'path': ' M {},{} L{},{} L{},{} L{},{} Z'.format(keelx1, keely1, keelx2, keely2, keelx3, keely3, keelx4, keely4),
            'layer': 'below', 'line': {'width': 1},
        },
        {  # rudder
            'type': 'path',
            'path': ' M {},{} L{},{} L{},{} L{},{} Z'.format(rudderx1, ruddery1, rudderx2, ruddery2, rudderx3, ruddery3, rudderx4, ruddery4),
            'layer': 'below', 'line': {'width': 1},
        },
        {  # deckcurve
            'type': 'path',
            'path': ' M 0,0 L{},{} L{},{} L{},{} L{},{} L{},{} Z'.format(deckx1, decky1, deckx2, decky2, deckx3, decky3, deckx4, decky4, deckx5, decky5),
            'fillcolor': 'white', 'layer': 'below', 'line': {'width': 1},
        },
        {  # keel curve
            'type': 'path',
            'path': 'M 0,0 C {},{} {},{} {},0'.format(lwl/3, -tc*1.35, 2*lwl/3, -tc*1.35, lwl),
            'fillcolor': 'white', 'layer': 'below', 'line': {'width': 1},
        },
        {  # boom
            'type': 'path',
            'path': ' M {},{} L{},{} L{},{} L{},{} Z'.format(boomx1, boomy1, boomx2-mastdiameter, boomy2, boomx3-mastdiameter, boomy3, boomx4, boomy4),
            'layer': 'above', 'fillcolor': 'white', 'line': {'width': 1},
        },
        {  # mast
            'type': 'path',
            'path': ' M {},{} L{},{} L{},{} L{},{} Z'.format(mastx1, masty1, mastx2, masty2, mastx3, masty3, mastx4, masty4),
            'layer': 'above', 'fillcolor': 'white', 'line': {'width': 1},
        },
        {  # main sail
            'type': 'path',
            'path': ' M {},{} L{},{} L{},{} Z'.format(boomx4, boomy4, boomx3, boomy3, mastx4, masty4),
            'layer': 'below', 'fillcolor': 'rgba(255, 140, 184, 0.1)', 'line': {'width': 1},
        },
        {  # jib sail
            'type': 'path',
            'path': ' M {},{} L{},{} L{},{} Z'.format(jibx1, jiby1, jibx2, jiby2, jibx3, jiby3) if jib else '',
            'layer': 'below', 'fillcolor': 'rgba(93, 164, 214, 0.1)', 'line': {'width': 1},
        },
        {  # spinnaker sail #1
            'type': 'path',
            'path': 'M {},{} Q {},{} {},{}'.format(lwl*0.65, freeboard+psail/8, lwl*0.85, freeboard+psail*0.15, deckx4, decky4) if spinnaker else '',
            'layer': 'below', 'line': {'width': 1},
        },
        {  # spinnaker sail #2
            'type': 'path',
            'path': 'M {},{} Q {},{} {},{}'.format(lwl*0.65, freeboard+psail/8, lwl*0.8, freeboard+psail/2, mastpos, freeboard+psail*0.9) if spinnaker else '',
            'layer': 'below', 'line': {'width': 1},
        },
        {  # spinnaker sail #3
            'type': 'path',
            'path': 'M {},{} Q {},{} {},{}'.format(mastpos, freeboard+psail*0.9, deckx4*1.1, freeboard+psail*0.8, deckx4, decky4) if spinnaker else '',
            'layer': 'below', 'line': {'width': 1},
        },
        {  # spinnaker line
            'type': 'line',
            'x0': lwl*0.65 if spinnaker else '', 'y0': freeboard+psail/8 if spinnaker else '',
            'x1': deckx3 if spinnaker else '', 'y1': decky3 if spinnaker else '',
            'layer': 'below', 'line': {'width': 1, 'color': 'grey'},
        },
        {  # main line
            'type': 'line', 'x0': deckx3, 'y0': decky3, 'x1': boomx2, 'y1': boomy2,
            'layer': 'below', 'line': {'width': 1, 'color': 'grey'},
        },
        {  # jib line
            'type': 'line', 'x0': cockpitx1, 'y0': cockpity1, 'x1': jibx2, 'y1': jiby2,
            'layer': 'below', 'line': {'width': 1, 'color': 'grey'},
        },
        {  # keel profile
            'type': 'path',
            'path': ' M {},{} L{},{} L{},{} L{},{} Z'.format(deckx4+1+boa/2-rootchordkeel*rootchordkeeltcks/2, 0, deckx4+1+boa/2+rootchordkeel*rootchordkeeltcks/2, 0, deckx4+1+boa/2+tipchordkeel*tipchordkeeltcks/2, -tc-spankeel, deckx4+1+boa/2-tipchordkeel*tipchordkeeltcks/2, -tc-spankeel),
            'layer': 'below', 'line': {'width': 1},
        },
        {  # rudder profile
            'type': 'path',
            'path': ' M {},{} L{},{} L{},{} L{},{} Z'.format(deckx4+1+boa/2-rootchordrudder*rootchordruddertcks/2, 0, deckx4+1+boa/2+rootchordrudder*rootchordruddertcks/2, 0, deckx4+1+boa/2+tipchordrudder*tipchordruddertcks/2, -heightsurfacerudder-spanrudder, deckx4+1+boa/2-tipchordrudder*tipchordruddertcks/2, -heightsurfacerudder-spanrudder),
            'layer': 'below', 'line': {'width': 1},
        },
        {  # deck profile
            'type': 'path',
            'path': 'M {},{} C {},{} {},{} {},{}'.format(deckx4+1, freeboard, deckx4+1+boa*0.05, -1.9*tc, deckx4+1+boa*0.95, -1.9*tc, deckx4+1+boa, freeboard),
            'line': {'width': 1}, 'fillcolor': 'white', 'layer': 'below',
        },
        {  # deck upper profile
            'type': 'path',
            'path': 'M {},{} Q {},{} {},{}'.format(deckx4+1, freeboard, deckx4+1+boa/2, freeboard*1.2, deckx4+1+boa, freeboard),
            'line': {'width': 1},
        },
        {  # mizzen mast
            'type': 'path',
            'path': ' M {},{} L{},{} L{},{} L{},{} Z'.format(deckx3, decky3, deckx3+mastdiameter, decky3, deckx3+mastdiameter, decky3+pmz+badmz, deckx3, decky3+pmz+badmz) if mizzen else '',
            'layer': 'above', 'fillcolor': 'white', 'line': {'width': 1},
        },
        {  # mizzen sail
            'type': 'path',
            'path': ' M {},{} L{},{} L{},{} Z'.format(deckx3, decky3+badmz, deckx3, decky3+pmz+badmz, deckx3-emz, decky3+badmz) if mizzen else '',
            'layer': 'below', 'fillcolor': 'rgba(255, 140, 184, 0.1)', 'line': {'width': 1},
        },
        {  # mizzen boom
            'type': 'path',
            'path': ' M {},{} L{},{} L{},{} L{},{} Z'.format(deckx3, decky3+badmz, deckx3-emz*1.1, decky3+badmz, deckx3-emz*1.1, decky3+badmz-mastdiameter, deckx3, decky3+badmz-mastdiameter) if mizzen else '',
            'layer': 'above', 'fillcolor': 'white', 'line': {'width': 1},
        },
        {  # waterline
            'type': 'line', 'x0': -100, 'y0': 0, 'x1': 100, 'y1': 0,
            'line': {'width': 1, 'color': '#444'},  # the original colour string was invalid, so Plotly drew it in its default grey
        },
    ]
    # drop the shapes that are switched off (empty path / position)
    shapes = [s for s in shapes if s.get('path', None) != '' and s.get('x0', None) != '']

    annotations = []
    ymin = keely3*1.5
    xmax = deckx5*1.1+2+boa
    if str(v.get('show-dimensions', '1')) == '1':
        dims = Dimensions()
        sx = deckx4+1               # left edge of the section view
        xc = sx+boa/2               # centre line of the section view
        bottom = -tc-spankeel       # keel tip
        y1 = bottom-0.45            # first dimension row under the boat
        # lengths
        dims.h(0, lwl, y1, 'LWL', lwl)
        dims.h(deckx1, deckx4, y1-0.55, 'LOA', deckx4-deckx1)
        # sails and rig
        dims.v(boomx2-0.45, boomy3, masty4, 'P', psail)
        dims.h(boomx2, boomx1, boomy3+0.35, 'E', esail, label_below=False)
        if jib:
            dims.v(deckx4+0.45, decky4, jiby3, 'I', isail)
            dims.h(deckx4-jsail, deckx4, freeboard*0.45, 'J', jsail)
        dims.v(mastpos-0.45, freeboard, boomy1, 'BAD', boomheight)
        dims.v(mastx2+0.3, masty1, masty4, 'EHM', masty4-masty1)
        if mizzen:
            dims.v(deckx3-emz-0.35, decky3+badmz, decky3+pmz+badmz, 'Pmz', pmz)
            dims.h(deckx3-emz, deckx3, decky3+badmz-0.4, 'Emz', emz)
        # keel and rudder
        dims.v(keelx4-0.35, -tc, bottom, 'SpanK', spankeel)
        dims.h(keelx3, keelx2, bottom-0.2, 'tipcK', tipchordkeel, label_below=False)
        dims.v(rudderx4-0.35, ruddery1, ruddery2, 'SpanR', spanrudder)
        # section view
        dims.h(sx, sx+boa, freeboard*1.2+0.45, 'BOA', boa)
        dims.h(xc-bwl/2, xc+bwl/2, y1, 'BWL', bwl)
        dims.v(sx+boa+0.35, 0, freeboard, 'fb', freeboard)
        dims.v(sx+boa+0.35, 0, -tc, 'Tc', tc, label_right=True)
        dims.v(sx+boa+0.95, 0, bottom, 'T', tc+spankeel)
        shapes = shapes + dims.shapes
        annotations = dims.annotations
        ymin = min(ymin, y1-1.1)
        xmax = max(xmax, sx+boa+1.6)

    def point(x, y, name):
        return go.Scatter(x=[x], y=[y], text=[name], name=name, cliponaxis=False, mode='markers')

    return go.figure(
        [
            point(lcf, 0, 'LCF'),
            point(lcb, 0, 'LCB'),
            point(cekeelx+poskeel, -cekeely-tc, 'CE Keel'),
            point(cerudderx+posrudder, -ceruddery-heightsurfacerudder, 'CE Rudder'),
            point(cesailx, cesaily, 'CE Aero'),
            point(cehidrox, cehidroy, 'CE Hydro'),
        ],
        go.Layout(
            height=800,
            xaxis={'range': [deckx1*1.1-emz-0.8, xmax], 'zeroline': False, 'title': "Length [m]", 'dtick': 1},
            yaxis={'range': [ymin, masty4*1.1], 'showgrid': False, 'title': "Height [m]", 'scaleanchor': "x", 'scaleratio': 1},
            annotations=annotations,
            margin={"r": 30, "t": 30, "b": 30, "l": 30},
            shapes=shapes,
            font=dict(size=10),
            legend=dict(x=0, y=1),
        ),
    )


SECTIONS = {
    'boa': lambda v: boa_fields(v['bwl-new']),
    'sail': lambda v: sail_fields(v['sailset'], v['disp-new'], v['lwl-new']),
    'rudder': lambda v: rudder_fields(v['lwl-new'], v['disp-new']),
    'keel': lambda v: keel_fields(v['lwl-new'], v['tc-new'], v['disp-new']),
    'mizzen': lambda v: mizzen_fields(v['mzn-check']),
    'bulb': lambda v: bulb_fields(v['bulbo-check']),
}


def fields(sections, values):
    """Default input boxes for the given sections (recomputed whenever the
    inputs they depend on change, as the Dash callbacks did)."""
    return {s: SECTIONS[s](values) for s in sections}


def view(values):
    return {'figure': side_plan(values), 'summary': summary(values)}


SAILSETS = {'1': 'main+genoa', '2': 'main+spinnaker', '3': 'main+genoa+spinnaker', '4': 'main'}
NACA = {'1': '4digit', '2': '6digit'}


def vpp_inputs(v, kg=0.8):
    """Map the values on this page to the inputs of functions/vpp.py (vpp_solve)."""
    f = lambda k: float(v[k])  # noqa: E731
    lwl, bwl, tc, disp = f('lwl-new'), f('bwl-new'), f('tc-new'), f('disp-new')
    loa = lwl+f('overhang')+math.tan(math.radians(f('bowangle')))*f('freeboard')
    # centres of effort as drawn in the side plan view
    geo = _centres(v)
    return dict(
        sailset=SAILSETS[str(v['sailset'])], loa=loa, lwl=lwl, boa=f('boa'), bwl=bwl, tc=tc,
        lcb=f('lcb-new')-lwl/2, lcf=f('lcf-new')-lwl/2,     # the VPP measures them from midship
        cb=disp/(lwl*bwl*tc), cm=0.7, cp=0.58, cwp=0.75,     # form coefficients: defaults of the Hull tab
        lat_surface_cb=lwl*tc*0.7, KG=float(kg), free_board=f('freeboard'),
        lead_rudder=geo['lead_rudder'], lead_sail=geo['lead_sail'], mass_crew=f('crewmass'),
        height_mainsail=f('psail'), base_mainsail=f('esail'), height_foretriangle=f('isail'), base_foretriangle=f('jsail'),
        boom_heigth_deck=f('boom-height'), length_spinnaker=f('spl'), perpendicular_jib=f('lpg'),
        span_rudder=f('span-rudder'), tip_chord_rudder=f('tipchord-rudder'), root_chord_rudder=f('rootchord-rudder'),
        tip_thickness_rudder=f('tipchord-rudder-tcks'), root_thickness_rudder=f('rootchord-rudder-tcks'),
        sweep_rudder_deg=f('sweep-rudder'), span_keel=f('span-keel'), tip_chord_keel=f('tipchord-keel'),
        root_chord_keel=f('rootchord-keel'), tip_thickness_keel=f('tipchord-keel-tcks'),
        root_thickness_keel=f('rootchord-keel-tcks'), sweep_keel_deg=f('sweep-keel'),
        naca_keel=NACA[str(v['keel-naca'])], naca_rudder=NACA[str(v['rudder-naca'])],
        height_mast=f('mast-height'), diameter_mast=f('mast-diameter'), height_surface_rudder=f('heightsurface-rudder'),
        height_mizzen=f('pmz'), base_mizzen=f('emz'), boom_height_mizzen=f('badmz'),
        chord_bulb_keel=f('lbk'), diameter_bulb=(f('abk')/f('lbk') if f('lbk') > 0 else 0.0), surface_area_bulb=f('sbk'),
    )


def _centres(v):
    """Hydrodynamic and aerodynamic centres of effort (same formulas as side_plan)."""
    sailset = int(v['sailset'])
    lwl, tc, freeboard = float(v['lwl-new']), float(v['tc-new']), float(v['freeboard'])
    bowangle = math.radians(float(v['bowangle']))
    poskeel, spankeel = float(v['pos-keel']), float(v['span-keel'])
    sweepkeel = math.radians(float(v['sweep-keel']))
    tipchordkeel, rootchordkeel = float(v['tipchord-keel']), float(v['rootchord-keel'])
    heightsurfacerudder, spanrudder = float(v['heightsurface-rudder']), float(v['span-rudder'])
    rootchordrudder, tipchordrudder = float(v['rootchord-rudder']), float(v['tipchord-rudder'])
    sweeprudder, posrudder = math.radians(float(v['sweep-rudder'])), float(v['pos-rudder'])
    psail, esail, isail, jsail = float(v['psail']), float(v['esail']), float(v['isail']), float(v['jsail'])
    boomheight, mastpos = float(v['boom-height']), float(v['mastpos'])
    deckx4 = (math.tan(bowangle)*freeboard)+lwl
    decky4 = freeboard*1.1
    keelx1 = poskeel+rootchordkeel/2
    keelx2 = keelx1-math.tan(sweepkeel)*spankeel
    keelx3 = keelx2-tipchordkeel
    rudderx1 = posrudder+rootchordrudder/2
    rudderx2 = rudderx1-math.tan(sweeprudder)*spanrudder
    rudderx3 = rudderx2-tipchordrudder
    arearudder = spanrudder*(rootchordrudder+tipchordkeel)/2
    areakeel = spankeel*(rootchordkeel+tipchordkeel)/2
    areahull = lwl*tc*0.7
    a, b = tipchordkeel, rootchordkeel
    cekeely = spankeel/3*((2*a+b)/(a+b))
    cekeelx = -(poskeel-(keelx2+keelx3)/2)/spankeel*cekeely
    ceruddery = spanrudder/3*((2*b+a)/(a+b))
    cerudderx = -(posrudder-(rudderx2+rudderx3)/2)/spanrudder*ceruddery
    cehidrox = ((cekeelx+poskeel)*areakeel+(cerudderx+posrudder)*arearudder+lwl/2*(areahull))/(areakeel+arearudder+areahull)
    mainarea = psail*esail/2
    if sailset == 1 or sailset == 3:
        jibarea = isail*jsail/2
        cesailx = (mainarea*(-esail/3+mastpos)+jibarea*(deckx4-jsail*2/3))/(mainarea+jibarea)
    else:
        cesailx = (-esail/3+mastpos)
    return {'lead_rudder': cehidrox-(cerudderx+posrudder), 'lead_sail': cesailx-cehidrox}


def polar(values, wind_min=6, wind_max=20, kg=0.8, progress=None):
    """Polar diagram from the VPP (functions/vpp.py) with the values on this page."""
    from functions.vpp import vpp_solve
    inputs = vpp_inputs(values, kg)
    report = (lambda done, total: progress(done, total)) if progress else None
    r = vpp_solve(**inputs, minimum_tw_knots=float(wind_min), maximum_tw_knots=float(wind_max)+0.5,
                  minimum_tw_angle=30, maximum_tw_angle=181, step_angle=5, details=True, progress=report)
    angles = r['angle_tw_deg']
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
    traces = []
    total = converged = 0
    for k, wind in enumerate(r['velocity_tw']):
        speeds = []
        for i in range(len(angles)):
            total += 1
            if r['converged'][k][i]:
                converged += 1
                speeds.append(round(r['velocity_boat'][k][i]/0.514444, 3))
            else:
                speeds.append(None)
        knots = wind/0.514444
        traces.append(dict(type='scatterpolar', theta=angles, r=speeds, mode='lines', connectgaps=False,
                           name='{:.0f} kn'.format(knots), line=dict(color=colors[k % len(colors)], width=2),
                           hovertemplate='TWS {:.0f} kn<br>TWA %{{theta}}&deg;<br>%{{r:.2f}} kn<extra></extra>'.format(knots)))
    fig = go.figure(traces, dict(
        title='Polar diagram: boat speed [kn] by true wind angle',
        height=560,
        margin={"r": 40, "t": 50, "b": 30, "l": 40},
        showlegend=True,
        legend=dict(title='True wind', x=0.0, y=0.0, xanchor='left', yanchor='bottom', font=dict(size=10)),
        polar=dict(
            sector=[-90, 90],
            angularaxis=dict(direction='clockwise', rotation=90, dtick=15, ticksuffix='°'),
            radialaxis=dict(angle=90, tickangle=90, rangemode='tozero'),
        ),
        font=dict(size=10),
    ))
    return {'figure': fig, 'converged': converged, 'total': total,
            'average_velocity': r['average_velocity']/0.514444, 'inputs': inputs}
