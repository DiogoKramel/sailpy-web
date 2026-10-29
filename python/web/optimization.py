"""Optimization tab (from callbacks/optimizationhullcall.py and
functions/platypus_resistance.py).

The Dash version kept the individuals in optimizationresistance.csv; here they
are kept in a list of rows with the same columns and number formatting.
"""
import time

from platypus import NSGAII, GDE3, OMOPSO, SMPSO, SPEA2, EpsMOEA, Problem, Real

from functions.resistance import resistance
from functions.resistance_added import calc_added_resistance

COLUMNS = ['id', 'Resistance', 'Rv', 'Ri', 'Rr', 'Rincli', 'Comfort', 'CS', 'LWL', 'BWL', 'Draft',
           'Displacement', 'AWP', 'LCB', 'LCF', 'constraint1', 'constraint2', 'constraint3',
           'constraint4', 'constraint5', 'valid']


def _r(value):
    # the CSV stored format(x, '.4f'); keep the same precision
    return float(format(value, '.4f'))


def _row(values):
    return dict(zip(COLUMNS, values))


def dimension_limits(dimensions):
    """Default limits shown under 'Dimensions optimized' for the current hull."""
    lwl, bwl, tc = float(dimensions['lwl']), float(dimensions['bwl']), float(dimensions['tc'])
    lcb, lcf = float(dimensions['lcb']), float(dimensions['lcf'])
    displacement = lwl*bwl*tc*0.38
    fmt = lambda x: "{}".format(round(x, 2))  # noqa: E731
    return {
        'current': {'lwl': "{}m".format(round(lwl, 2)), 'bwl': "{}m".format(round(bwl, 2)),
                    'tc': "{}m".format(round(tc, 2)), 'lcb': "{}m".format(round(lcb, 2)),
                    'lcf': "{}m".format(round(lcf, 2))},
        'values': {
            'lwl-min': fmt(lwl*0.9), 'lwl-max': fmt(lwl*1.1),
            'bwl-min': fmt(bwl*0.85), 'bwl-max': fmt(bwl*1.15),
            'tc-min': fmt(tc*0.85), 'tc-max': fmt(tc*1.15),
            'displac': fmt(displacement), 'gyration': fmt(0.25), 'ballast-ratio': fmt(40),
            'lcb-min': fmt(lwl*0.418), 'lcb-max': fmt(lwl*0.5),
            'lcf-min': fmt(lwl*0.405), 'lcf-max': fmt(lwl*0.482),
            'cwp-min': fmt(0.68), 'cwp-max': fmt(0.71),
            'cp-min': fmt(0.52), 'cp-max': fmt(0.6),
            'cm-min': fmt(0.65), 'cm-max': fmt(0.78),
        },
    }


def run(dimensions, settings, progress=None):
    """Run the hull optimization. ``settings`` holds the Optimization tab inputs."""
    offspringsplatypus = int(float(settings['offsprings']))
    gamethod = settings['gamethod']
    velocityrange = [int(v) for v in settings['velocityrange']]
    heelrange = [int(v) for v in settings['heelrange']]
    lim = {k: float(v) for k, v in settings['limits'].items()}

    rows = []

    # initial hull (first line of the results)
    lwl = float(dimensions["lwl"])
    bwl = float(dimensions["bwl"])
    tc = float(dimensions["tc"])
    cp = float(dimensions["cp"])
    cm = float(dimensions["cm"])
    cwp = float(dimensions["cwp"])
    disp = float(dimensions["disp"])
    lcf = float(dimensions["lcf"])
    lcb = float(dimensions["lcb"])
    Rt, CR, Rv, Ri, Rr, Rincli, count = 0, 0, 0, 0, 0, 0, 0
    for velocity in range(velocityrange[0], velocityrange[1], 1):
        for heel in range(heelrange[0], heelrange[1], 5):
            result = resistance(lwl, bwl, tc, cp, cm, cwp, disp, lcb, lcf, velocity, heel)
            Rt = Rt+result[0]
            Rv = Rv+result[1]
            Ri = Ri+result[2]
            Rr = Rr+result[3]
            Rincli = Rincli+result[4]
            CR = CR+result[5]
            count = count+1
    Rt, CR, Rv, Ri, Rr = Rt/count, CR/count, Rv/count, Ri/count, Rr/count
    boa = bwl*1.1
    dispmass = disp*1025
    cs = boa*3.28084/(dispmass*2.20462/64)**(1/3)
    rows.append(_row([1, _r(Rt), _r(Rv), _r(Ri), _r(Rr), _r(Rincli), _r(CR), _r(cs), _r(lwl), _r(bwl), _r(tc),
                      _r(disp), _r(cwp), _r(lcb), _r(lcf), False, False, False, False, False, False]))

    start = time.time()
    gyration = 0.2
    wave_angle = 140
    wl_sl = 0.5
    wave_height = 2
    displac = lim['displac']

    def function_platypus(vars):
        # each vars[i] give one random number between the minimum and maximum limit for each parameter
        lwl, bwl, tc, lcf, lcb, cwp, cp, cm = vars[0], vars[1], vars[2], vars[3], vars[4], vars[5], vars[6], vars[7]

        # calculate remaining parameters
        disp = float(displac)
        awp = bwl*lwl*cwp
        boa = bwl*1.1
        dispmass = disp*1025
        cs = boa*3.28084/(dispmass*2.20462/64)**(1/3)
        cb = disp/(lwl*bwl*tc)

        # calculate the resistance for a combinantion of velocities and heel angle
        Rt, CR, Rv, Ri, Rr, Rincli, count, Radd = 0, 0, 0, 0, 0, 0, 0, 0
        for velocity in range(velocityrange[0], velocityrange[1], 1):
            for heel in range(heelrange[0], heelrange[1], 5):
                froude_number = velocity/(9.81 * lwl) ** 0.5
                result = resistance(lwl, bwl, tc, cp, cm, cwp, disp, lcb, lcf, velocity, heel)
                froude_number = 0.3
                result2 = calc_added_resistance(disp, lwl, bwl, tc, cp, wave_angle, froude_number, gyration, wl_sl, wave_height)
                Rt, Rv, Ri, Rr, Rincli, CR, count = Rt+result[0], Rv+result[1], Ri+result[2], Rr+result[3], Rincli+result[4], CR+result[5], count+1
                Radd = Radd + abs(result2)
        Rt, CR, Rv, Ri, Rr, Rincli, Radd = Rt/count, CR/count, Rv/count, Ri/count, Rr/count, Rincli/count, Radd/count

        # the CSV line number in the original = number of rows + header
        index = len(rows) + 1

        # calculate constraints of delft series, capsize screening factor, and displacement
        constraint1, constraint2, constraint3, constraint4, constraint5, constraint6, valid = False, False, False, False, False, False, False
        if (lwl/bwl) > 5 or (lwl/bwl) < 2.73:
            constraint1 = True
        if (bwl/tc) > 6.5 or (bwl/tc) < 3.8:  # (bwl/tcan) > 19.39 or (bwl/tcan) < 2.46 delft series seems to have unrealistic limits
            constraint2 = True
        if (lwl/disp**(1/3)) > 8.5 or (lwl/disp**(1/3)) < 4.34:
            constraint3 = True
        if (awp/disp**(2/3)) > 12.67 or (awp/disp**(2/3)) < 3.78:
            constraint4 = True
        if cs > 2:
            constraint5 = True
        if cb < 0.35:
            constraint6 = True
        if constraint1 == False and constraint2 == False and constraint3 == False and constraint4 == False and constraint5 == False and constraint6 == False:  # noqa: E712
            valid = True

        rows.append(_row([index, _r(Rt), _r(Rv), _r(Ri), _r(Rr), _r(Rincli), _r(CR), _r(cs), _r(lwl), _r(bwl), _r(tc),
                          _r(disp), _r(cwp), _r(lcb), _r(lcf), constraint1, constraint2, constraint3, constraint4, constraint5, valid]))
        if progress is not None and len(rows) % 5 == 0:
            progress(len(rows) - 1, offspringsplatypus)

        # return 2 objectives and 5 restrictions
        return [Rt, CR], [cs-2, lwl/bwl-5, 2.73-lwl/bwl, bwl/tc-6.5, 3.8-bwl/tc]

    # optimize for 8 parameters, 2 objectives and 5 restrictions
    problem = Problem(8, 2, 5)
    problem.types[:] = [Real(lim['lwlmin'], lim['lwlmax']), Real(lim['bwlmin'], lim['bwlmax']), Real(lim['tcmin'], lim['tcmax']),
                        Real(lim['lcfmin'], lim['lcfmax']), Real(lim['lcbmin'], lim['lcbmax']), Real(lim['cwpmin'], lim['cwpmax']),
                        Real(lim['cpmin'], lim['cpmax']), Real(lim['cmmin'], lim['cmmax'])]
    problem.directions[:] = [Problem.MINIMIZE, Problem.MAXIMIZE]
    problem.constraints[:] = "<0"
    problem.function = function_platypus

    # six methods applied (there is four more still not applied)
    if gamethod == 'NSGAII':
        algorithm = NSGAII(problem)
    elif gamethod == 'GDE3':
        algorithm = GDE3(problem)
    elif gamethod == 'OMOPSO':
        algorithm = OMOPSO(problem, epsilons=0.05)
    elif gamethod == 'SMPSO':
        algorithm = SMPSO(problem)
    elif gamethod == 'SPEA2':
        algorithm = SPEA2(problem)
    elif gamethod == 'EpsMOEA':
        algorithm = EpsMOEA(problem, epsilons=0.05)
    else:
        raise ValueError('Unknown method {}'.format(gamethod))

    algorithm.run(offspringsplatypus)
    elapsed = time.time() - start
    if progress is not None:
        progress(len(rows) - 1, offspringsplatypus)

    return {
        'rows': rows,
        'gamethod': gamethod,
        'elapsed': round(elapsed, 2),
        'message': "Optimization finished in {} seconds after generating {} offsprings".format(round(elapsed, 2), len(rows)),
    }
