##! 
##! Copyright(c) 2022, 2023 Stanford Research Systems, All rights reserved
##! Subject to the MIT License
##! 

import numpy as np
from numpy.linalg import norm

from scipy import sparse
from scipy.sparse import linalg


def calculate_baseline(y, ratio=1e-6, lam=1e4, niter=20, full_output=False):
    """
    Calculate baseline of a spectrum based on
    Asymmetrically reweighted penalized least square (ARPLS)

    Original paper:
    https://pubs.rsc.org/en/content/articlelanding/2015/AN/C4AN01061B#!divAbstract

    Python implementation:
    https://stackoverflow.com/questions/29156532/python-baseline-correction-library

    Parameters
    -----------
        y: Numpy array
            Intensity array
        ratio: float
            improvement ratio to reach before stopping iteration
        lam: float
            fit parameter lambda
        niter: int
            maximum iteration
        full_output: bool, optional
            generate detailed output

    Returns
    --------
        Numpy array
            baseline array, if full_output == False
        tuple
            (baseline array, baseline-subtracted intensity array,
            termination information in dict format),
            if full_output == True

    """
    L = len(y)

    diag = np.ones(L - 2)
    D = sparse.spdiags([diag, -2 * diag, diag], [0, -1, -2], L, L - 2)

    H = lam * D.dot(D.T)  # The transposes are flipped w.r.t the Algorithm on pg. 252

    w = np.ones(L)
    W = sparse.spdiags(w, 0, L, L)

    crit = 1
    count = 0

    while crit > ratio:
        z = linalg.spsolve(W + H, W * y)
        d = y - z
        dn = d[d < 0]

        m = np.mean(dn)
        s = np.std(dn)

        w_new = 1 / (1 + np.exp(np.clip(2 * (d - (2 * s - m)) / s, -20, 20)))
        crit = norm(w_new - w) / norm(w)

        w = w_new
        W.setdiag(w)  # Do not create a new matrix, just update diagonal values

        count += 1

        if count > niter:
            # print('Maximum number of iterations exceeded')
            break

    if full_output:
        info = {'num_iter': count, 'stop_criterion': crit}
        return z, d, info
    else:
        return z


def get_peak_from_analog_scan(x, y, mass, fit=False):
    """
    Calculate the intensity of a peak in an analog scan spectrum

    Parameters
    -----------
        x: Numpy array
            mass axis values
        y: Numpy array
            intensity array
        mass: float
            peak position within the range of x
        fit: bool, optional
            The default is False, if False, return the maximum value around mass.
            If True , it fits the data around x with a parabola, and calculate
            the maximum of the parabola.
    Returns
    --------
        float
            peak intensity
    """
    distance = 0.5
    m = np.where((x > mass - distance) & (x < mass + distance))[0]
    if len(m) < 5:
        return 0.0
    p = np.max(y[m])
    if not fit:
        return p

    arg = m[0] + np.argmax(y[m])
    x1 = x[arg - 2:arg + 4]
    y1 = y[arg - 2:arg + 4]
    c = np.polyfit(x1, y1, 2)  # fit the points around the max
    roots = np.roots(c)
    pp = (roots[0] + roots[1]) / 2.0  # peak position
    pp = pp.real
    pi = np.polyval(c, pp)  # c[0] + c[1] * pp + c[2] * pp ** 2  # peak intensity
    return pi
