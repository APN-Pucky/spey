"""Tools for computing upper limit on parameter of interest"""

from typing import Callable, Tuple, Text, List, Union
from functools import partial
import warnings, scipy
import numpy as np

from spey.hypothesis_testing.test_statistics import compute_teststatistics
from spey.utils import ExpectationType
from .utils import compute_confidence_level

__all__ = ["find_poi_upper_limit", "find_root_limits"]


def find_root_limits(
    computer: Callable[[float], float], loc: float = 0.0, low_ini: float = 1.0, hig_ini: float = 1.0
) -> Tuple[float, float]:
    """
    Find limits for brent bracketing

    :param hig_ini:
    :param low_ini:
    :param computer: POI dependent function
    :param loc: location of the root
    :return: lower and upper bound
    """
    assert callable(computer), "Invalid input. Computer must be callable."

    low, hig = low_ini, hig_ini
    while computer(low) > loc:
        low *= 0.5
        if low < 1e-10:
            break
    while computer(hig) < loc:
        hig *= 2.0
        if hig > 1e10:
            break
    return low, hig


def find_poi_upper_limit(
    maximum_likelihood: Tuple[float, float],
    logpdf: Callable[[float], float],
    maximum_asimov_likelihood: Tuple[float, float],
    asimov_logpdf: Callable[[float], float],
    expected: ExpectationType,
    confidence_level: float = 0.95,
    allow_negative_signal: bool = True,
    low_init: float = 1.0,
    hig_init: float = 1.0,
    expected_pvalue: Text = "nominal",
    maxiter: int = 10000,
) -> Union[float, List[float]]:
    """
    Compute the upper limit on parameter of interest, described by the confidence level

    :param maximum_likelihood (`Tuple[float, float]`): muhat and minimum negative log-likelihood
    :param logpdf (`Callable[[float], float]`): log of the full density
    :param maximum_asimov_likelihood (`Tuple[float, float]`): muhat and minimum negative
                                                              log-likelihood for asimov data
    :param asimov_logpdf (`Callable[[float], float]`): log of the full density for asimov data
    :param expected (`ExpectationType`): observed, apriori or aposteriori
    :param confidence_level (`float`, default `0.95`): exclusion confidence level (default 1 - CLs = 95%).
    :param allow_negative_signal (`bool`, default `True`): allow negative signals while
                                                           minimising negative log-likelihood.
    :param low_init (`float`, default `1.0`): initialized lower bound for bracketing.
    :param hig_init (`float`, default `1.0`): initialised upper bound for bracketing.
    :param expected_pvalue (`Text`, default `"nominal"`): find the upper limit for pvalue range,
                                                    only for expected. `nominal`, `1sigma`, `2sigma`
    :param maxiter (`int`, default `200`): If convergence is not achieved in maxiter iterations,
                                           an error is raised. Must be >= 0.
    :return `Union[float, List[float]]`: excluded parameter of interest
    """
    assert expected_pvalue in [
        "nominal",
        "1sigma",
        "2sigma",
    ], f"Unknown pvalue range {expected_pvalue}"
    if expected is ExpectationType.observed:
        expected_pvalue = "nominal"
    test_stat = "q" if allow_negative_signal else "qtilde"

    # make sure that initial values are not nan or None
    low_init = 1.0 if not low_init or not np.isnan(low_init) else low_init
    hig_init = 1.0 if not hig_init or not np.isnan(hig_init) else hig_init

    def computer(poi_test: float, pvalue_idx: int) -> float:
        """Compute 1 - CLs(POI) = `confidence_level`"""
        _, sqrt_qmuA, delta_teststat = compute_teststatistics(
            poi_test,
            maximum_likelihood,
            logpdf,
            maximum_asimov_likelihood,
            asimov_logpdf,
            test_stat,
        )
        pvalue = list(
            map(
                lambda x: 1.0 - x,
                compute_confidence_level(sqrt_qmuA, delta_teststat, test_stat)[
                    0 if expected == ExpectationType.observed else 1
                ],
            )
        )
        # always get the median
        return pvalue[pvalue_idx] - confidence_level

    result = []
    index_range = {
        "nominal": [0 if expected is ExpectationType.observed else 2],
        "1sigma": range(1, 4),
        "2sigma": range(0, 5),
    }
    for pvalue_idx in index_range[expected_pvalue]:
        comp = partial(computer, pvalue_idx=pvalue_idx)
        low, hig = find_root_limits(comp, loc=0.0, low_ini=low_init, hig_ini=hig_init)
        with warnings.catch_warnings(record=True):
            x0, r = scipy.optimize.toms748(
                comp, low, hig, k=2, xtol=2e-12, rtol=1e-4, full_output=True, maxiter=maxiter
            )
        if not r.converged:
            warnings.warn(f"Optimiser did not converge.\n{r}", category=RuntimeWarning)
        result.append(x0)
    return result if len(result) > 1 else result[0]