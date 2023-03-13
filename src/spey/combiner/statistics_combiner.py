from typing import List, Text, Generator, Any, Tuple, Union
import warnings, scipy
import numpy as np

from spey.interface.statistical_model import StatisticalModel
from spey.utils import ExpectationType
from spey.system.exceptions import AnalysisQueryError, NegativeExpectedYields
from spey.base.recorder import Recorder
from spey.base.hypotest_base import HypothesisTestingBase

__all__ = ["StatisticsCombiner"]


class StatisticsCombiner(HypothesisTestingBase):
    """
    Statistical model combination routine

    :param args: Statistical models
    """

    __slots__ = ["_statistical_models", "_recorder"]

    def __init__(self, *args):
        self._statistical_models = []
        self._recorder = Recorder()
        for arg in args:
            self.append(arg)

    def append(self, statistical_model: StatisticalModel) -> None:
        """
        Add new analysis to the statistical model stack

        :param statistical_model: statistical model to be added to the stack
        :raises AnalysisQueryError: if analysis name matches with another analysis within the stack
        """
        if isinstance(statistical_model, StatisticalModel):
            if statistical_model.analysis in self.analyses:
                raise AnalysisQueryError(f"{statistical_model.analysis} already exists.")
            self._statistical_models.append(statistical_model)
        else:
            raise TypeError(f"Can not append type {type(statistical_model)}.")

    def remove(self, analysis: Text) -> None:
        """Remove a specific analysis from the model list"""
        to_remove = None
        for name, model in self.items():
            if name == analysis:
                to_remove = model
        if to_remove is None:
            raise AnalysisQueryError(f"'{analysis}' is not among the analyses.")
        self._statistical_models.remove(to_remove)

    @property
    def statistical_models(self) -> List[StatisticalModel]:
        """Retreive the list of statistical models"""
        return self._statistical_models

    @property
    def analyses(self) -> List[Text]:
        """List of analyses that are included in combiner database"""
        return [model.analysis for model in self]

    @property
    def minimum_poi(self) -> float:
        """Find minimum POI test that can be applied to this statistical model"""
        return max(model.backend.model.minimum_poi for model in self)

    @property
    def isAlive(self) -> bool:
        """Is there any statistical model with non-zero signal yields in any region"""
        return any(model.isAlive for model in self)

    def __getitem__(self, item: Union[Text, int]) -> StatisticalModel:
        """Retrieve a statistical model"""
        if isinstance(item, int):
            if item < len(self):
                return self.statistical_models[item]
            raise AnalysisQueryError("Request exceeds number of statistical models available.")
        if isinstance(item, slice):
            return self.statistical_models[item]

        for model in self:
            if model.analysis == item:
                return model
        raise AnalysisQueryError(f"'{item}' is not among the analyses.")

    def __iter__(self) -> StatisticalModel:
        """Iterate over statistical models"""
        yield from self._statistical_models

    def __len__(self):
        """Number of statistical models within the stack"""
        return len(self._statistical_models)

    def items(self) -> Generator[tuple[Any, Any], Any, None]:
        """Returns a generator for analysis name and corresponding statistical model"""
        return ((model.analysis, model) for model in self)

    def find_most_sensitive(self) -> StatisticalModel:
        """
        Find the most sensitive statistical model which will return
        the model with minimum expected excluded cross-section
        """
        results = [model.s95exp for model in self]
        return self[results.index(min(results))]

    def likelihood(
        self,
        poi_test: float = 1.0,
        expected: ExpectationType = ExpectationType.observed,
        return_nll: bool = True,
        **kwargs,
    ) -> float:
        """
        Compute the likelihood for the statistical model with a given POI

        :param poi_test: POI (signal strength)
        :param expected: observed, apriori or aposteriori
        :param return_nll: if true returns negative log-likelihood value
        :param isAsimov: if true, computes likelihood for Asimov data
        :param kwargs: model dependent arguments. In order to specify backend specific inputs
                       provide the input in the following format

        .. code-block:: python3

            >>> from spey import AvailableBackends
            >>> kwargs = {
            >>>     str(AvailableBackends.pyhf): {"iteration_threshold": 3},
            >>>     str(AvailableBackends.simplified_likelihoods): {"marginalize": False},
            >>> }

        This will allow keyword arguments to be chosen with respect to specific backend.

        :return: likelihood value
        """
        nll = 0.0
        for statistical_model in self:

            current_kwargs = {}
            current_kwargs.update(kwargs.get(str(statistical_model.backend_type), {}))

            try:
                nll += statistical_model.likelihood(
                    poi_test=poi_test,
                    expected=expected,
                    **current_kwargs,
                )
            except NegativeExpectedYields as err:
                warnings.warn(
                    err.args[0] + f"\nSetting NLL({poi_test:.3f}) = nan",
                    category=RuntimeWarning,
                )
                nll = np.nan

            if np.isnan(nll):
                break

        return nll if return_nll or np.isnan(nll) else np.exp(-nll)

    def asimov_likelihood(
        self,
        poi_test: float = 1.0,
        expected: ExpectationType = ExpectationType.observed,
        return_nll: bool = True,
        test_statistics: Text = "qtilde",
        **kwargs,
    ) -> float:
        """
        Compute likelihood for the asimov data

        :param poi_test (`float`, default `1.0`): parameter of interest.
        :param expected (`ExpectationType`, default `ExpectationType.observed`):
                                                    observed, apriori or aposteriori.
        :param return_nll (`bool`, default `True`): if false returns likelihood value.
        :param test_statistics (`Text`, default `"qtilde"`): test statistics.
                    `"qmu"` or `"qtilde"` for exclusion tests `"q0"` for discovery test.
        :return `float`: likelihood computed for asimov data
        """
        nll = 0.0
        for statistical_model in self:

            current_kwargs = {}
            current_kwargs.update(kwargs.get(str(statistical_model.backend_type), {}))

            nll += statistical_model.asimov_likelihood(
                poi_test=poi_test,
                expected=expected,
                test_statistics=test_statistics,
                **current_kwargs,
            )

            if np.isnan(nll):
                break

        return nll if return_nll or np.isnan(nll) else np.exp(-nll)

    def maximize_likelihood(
        self,
        return_nll: bool = True,
        expected: ExpectationType = ExpectationType.observed,
        allow_negative_signal: bool = True,
        poi_upper_bound: float = 10.0,
        maxiter: int = 200,
        **kwargs,
    ) -> Tuple[float, float]:
        """
        Minimize negative log-likelihood of the statistical model with respect to POI

        :param return_nll: if true returns negative log-likelihood value
        :param expected: observed, apriori or aposteriori
        :param allow_negative_signal: if true, allow negative mu
        :param poi_upper_bound: Set upper bound for POI
        :param maxiter: number of iterations to be held for convergence of the fit.
        :param kwargs: model dependent arguments. In order to specify backend specific inputs
                       provide the input in the following format

        **Note:** Sigma mu has not yet been implemented, hence this function
        returns muhat, nan, negative log-likelihood

        .. code-block:: python3

            >>> import spey
            >>> combiner = spey.StatisticsCombiner(stat_model1, stat_model2)
            >>> kwargs = {
            >>>     str(spey.AvailableBackends.pyhf): {"iteration_threshold": 20},
            >>>     str(spey.AvailableBackends.simplified_likelihoods): {"marginalize": False},
            >>> }
            >>> muhat, _, nll_min = combiner.maximize_likelihood(
            >>>     return_nll=True,
            >>>     expected=spey.ExpectationType.apriori,
            >>>     allow_negative_signal=True,
            >>>     **kwargs
            >>> )

        This will allow keyword arguments to be chosen with respect to specific backend.
        :return: POI that minimizes the negative log-likelihood, minimum negative log-likelihood
        """
        # muhat initial value estimation
        _mu, _sigma_mu = np.zeros(len(self)), np.ones(len(self))
        for idx, stat_model in enumerate(self):
            _mu[idx] = stat_model.maximize_likelihood(expected=expected)[0]
            _sigma_mu[idx] = stat_model.sigma_mu(_mu[idx], expected=expected)
        mu_init = np.sum(np.power(_sigma_mu, -2)) * np.sum(
            np.true_divide(_mu, np.square(_sigma_mu))
        )

        def twice_nll(mu: Union[np.ndarray, float]) -> float:
            """Compute twice negative log likelihood"""
            return 2.0 * self.likelihood(
                mu if isinstance(mu, float) else mu[0], expected=expected, **kwargs
            )

        # It is possible to allow user to modify the optimiser properties in the future
        opt = scipy.optimize.minimize(
            twice_nll,
            mu_init,
            method="SLSQP",
            bounds=[(self.minimum_poi if allow_negative_signal else 0.0, poi_upper_bound)],
            tol=1e-6,
            options={"maxiter": maxiter},
        )

        if not opt.success:
            raise RuntimeWarning("Optimiser was not able to reach required precision.")

        nll, muhat = opt.fun / 2.0, opt.x

        return muhat, nll if return_nll else np.exp(-nll)

    def maximize_asimov_likelihood(
        self,
        return_nll: bool = True,
        expected: ExpectationType = ExpectationType.observed,
        test_statistics: Text = "qtilde",
        poi_upper_bound: float = 40.0,
        **kwargs,
    ) -> Tuple[float, float]:
        """
        Find maximum of the likelihood for the asimov data

        :param expected (`ExpectationType`): observed, apriori or aposteriori,.
            (default `ExpectationType.observed`)
        :param return_nll (`bool`): if false, likelihood value is returned.
            (default `True`)
        :param test_statistics (`Text`): test statistics. `"qmu"` or `"qtilde"` for exclusion
                                     tests `"q0"` for discovery test. (default `"qtilde"`)
        :return `Tuple[float, float]`: muhat, negative log-likelihood
        """
        allow_negative_signal: bool = True if test_statistics in ["q", "qmu"] else False

        def twice_nll(mu: Union[np.ndarray, float]) -> float:
            """Compute twice negative log likelihood"""
            return 2.0 * self.asimov_likelihood(
                mu if isinstance(mu, float) else mu[0], expected=expected, **kwargs
            )

        # It is possible to allow user to modify the optimiser properties in the future
        opt = scipy.optimize.minimize(
            twice_nll,
            [0.0],
            method="SLSQP",
            bounds=[(self.minimum_poi if allow_negative_signal else 0.0, poi_upper_bound)],
            tol=1e-6,
            options={"maxiter": 10000},
        )

        if not opt.success:
            raise RuntimeWarning("Optimiser was not able to reach required precision.")

        nll, muhat = opt.fun / 2.0, opt.x

        return muhat, nll if return_nll else np.exp(-nll)
