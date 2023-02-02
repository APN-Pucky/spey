from scipy.stats import multivariate_normal
from numpy import nan, inf

__all__ = ["AsymptoticTestStatisticsDistribution"]


class AsymptoticTestStatisticsDistribution:
    """
    The distribution the test statistic in the asymptotic case.

    :param shift: The displacement of the test statistic distribution.
    """

    __slots__ = ["shift", "cutoff"]

    def __init__(self, shift: float, cutoff: float = -inf):
        self.shift = shift
        self.cutoff = cutoff

    def pvalue(self, value: float) -> float:
        """
        The p-value for a given value of the test statistic corresponding
        to signal strength \mu and Asimov strength \mu as
        defined in Equations (59) and (57) of :xref:`arXiv:1007.1727`

        :param value: The test statistic value.
        :return: The integrated probability to observe a value at
                 least as large as the observed one.
        """
        return_value = multivariate_normal.cdf(self.shift - value)
        return return_value if return_value >= self.cutoff else nan

    def cdf(self, value: float) -> float:
        """
        Compute the value of the cumulative distribution function
        for a given value of the test statistic.

        :param value: The test statistic value.
        :return: The integrated probability to observe a test statistic
                 less than or equal to the observed value.
        """
        return multivariate_normal.cdf(value - self.shift)

    def expected_value(self, nsigma: float) -> float:
        """
        Return the expected value of the test statistic.

        :param nsigma: The number of standard deviations.
        :return: The expected value of the test statistic.
        """
        tot = nsigma + self.shift
        return tot if tot > self.cutoff else self.cutoff