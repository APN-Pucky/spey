import numpy as np
import warnings

from typing import Callable, Union, Tuple, Text, List, Optional

from madstats.tools.asymptotic_calculator import AsymptoticTestStatisticsDistribution
from madstats.utils import ExpectationType

__all__ = [
    "compute_confidence_level",
    "teststatistics",
    "find_root_limits",
    "pvalues",
    "expected_pvalues",
]


def compute_confidence_level(
    sqrt_qmuA: float,
    test_statistic: float,
    expected: Optional[ExpectationType] = ExpectationType.observed,
    test_stat: Text = "qtilde",
) -> List[float]:
    """
    Compute confidence level

    :param sqrt_qmuA: The calculated test statistic for asimov data
    :param test_statistic: test statistics
    :param expected: observed, apriori or aposteriori
    :param test_stat: type of test statistics
    :return: confidence limit
    """
    sig_plus_bkg_distribution = AsymptoticTestStatisticsDistribution(-sqrt_qmuA, -np.inf)
    bkg_only_distribution = AsymptoticTestStatisticsDistribution(0.0, -np.inf)

    if expected in [ExpectationType.observed, ExpectationType.apriori]:
        CLsb, CLb, CLs = pvalues(test_statistic, sig_plus_bkg_distribution, bkg_only_distribution)
    else:
        CLsb, CLb, CLs = expected_pvalues(sig_plus_bkg_distribution, bkg_only_distribution)

    if test_stat == "qtilde":
        return CLs

    return CLsb


def teststatistics(
    poi_test: Union[float, np.ndarray],
    negloglikelihood_asimov: Union[Callable[[np.ndarray], float], float],
    min_negloglikelihood_asimov: float,
    negloglikelihood: Union[Callable[[np.ndarray], float], float],
    min_negloglikelihood: float,
    test_stat: Text = "qtilde",
) -> Tuple[float, float, float]:
    """

    :param poi_test: POI (signal strength)
    :param negloglikelihood_asimov: POI dependent negative log-likelihood function
                                    based on asimov data
    :param min_negloglikelihood_asimov: minimum negative log-likelihood for asimov data
    :param negloglikelihood: POI dependent negative log-likelihood function
    :param min_negloglikelihood: minimum negative log-likelihood
    :param test_stat: The test statistic to use as a numerical summary of the data:
                      `qtilde`, `q`, or `q0`.
    :return: sqrt_qmu, sqrt_qmuA, test_statistics
    """
    if isinstance(poi_test, (float, int)):
        poi_test = np.array([float(poi_test)])
    elif len(poi_test) == 0:
        poi_test = np.array([poi_test])

    if callable(negloglikelihood_asimov):
        nllA = negloglikelihood_asimov(poi_test)
    else:
        nllA = negloglikelihood_asimov

    if callable(negloglikelihood):
        nll = negloglikelihood(poi_test)
    else:
        nll = negloglikelihood

    qmu = 0.0 if 2.0 * (nll - min_negloglikelihood) < 0.0 else 2.0 * (nll - min_negloglikelihood)
    qmuA = max(2.0 * (nllA - min_negloglikelihood_asimov), 0.0)
    sqrt_qmu, sqrt_qmuA = np.sqrt(qmu), np.sqrt(qmuA)

    if test_stat in ["q", "q0"]:
        test_statistics = sqrt_qmu - sqrt_qmuA
    else:
        if sqrt_qmu <= sqrt_qmuA:
            test_statistics = sqrt_qmu - sqrt_qmuA
        else:
            test_statistics = (qmu - qmuA) / (2.0 * sqrt_qmuA)

    return sqrt_qmu, sqrt_qmuA, test_statistics


def pvalues(
    teststatistic: float,
    sig_plus_bkg_distribution: AsymptoticTestStatisticsDistribution,
    bkg_only_distribution: AsymptoticTestStatisticsDistribution,
) -> Tuple[List[float], List[float], List[float]]:
    """
    Calculate the :math:`p`-values for the observed test statistic under the
    signal + background and background-only model hypotheses.

    :param teststatistic: The test statistic.
    :param sig_plus_bkg_distribution: The distribution for the signal + background hypothesis.
    :param bkg_only_distribution: The distribution for the background-only hypothesis.
    :return: The p-values for the test statistic corresponding to the `\mathrm{CL}_{s+b}`,
            `\mathrm{CL}_{b}`, and `\mathrm{CL}_{s}`.
    """
    CLsb = sig_plus_bkg_distribution.pvalue(teststatistic)
    CLb = bkg_only_distribution.pvalue(teststatistic)
    with warnings.catch_warnings(record=True):
        CLs = np.true_divide(CLsb, CLb, dtype=np.float32)
    return [CLsb], [CLb], [CLs if CLb != 0.0 else 0.0]


def expected_pvalues(
    sig_plus_bkg_distribution: AsymptoticTestStatisticsDistribution,
    bkg_only_distribution: AsymptoticTestStatisticsDistribution,
) -> List[List]:
    """
    Calculate the `\mathrm{CL}_{s}` values corresponding to the
    median significance of variations of the signal strength from the
    background only hypothesis `\left(\mu=0\right)` at
    `(-2,-1,0,1,2)\sigma`.

    :param sig_plus_bkg_distribution: The distribution for the signal + background hypothesis.
    :param bkg_only_distribution: The distribution for the background-only hypothesis.
    :return: The p-values for the test statistic corresponding to the `\mathrm{CL}_{s+b}`,
            `\mathrm{CL}_{b}`, and `\mathrm{CL}_{s}`.
    """
    return list(
        map(
            list,
            zip(
                *[
                    pvalues(
                        bkg_only_distribution.expected_value(nsigma),
                        sig_plus_bkg_distribution,
                        bkg_only_distribution,
                    )
                    for nsigma in [2.0, 1.0, 0.0, -1.0, -2.0]
                ]
            ),
        )
    )


def find_root_limits(computer: Callable[[float], float], loc: float = 0.0) -> Tuple[float, float]:
    """
    Find limits for brent bracketing

    :param computer: POI dependent function
    :param loc: location of the root
    :return: lower and upper bound
    """
    assert callable(computer), "Invalid input. Computer must be callable."

    low, hig = 1.0, 1.0
    while computer(low) > loc:
        low *= 0.1
        if low < 1e-10:
            break
    while computer(hig) < loc:
        hig *= 10.0
        if hig > 1e10:
            break
    return low, hig
