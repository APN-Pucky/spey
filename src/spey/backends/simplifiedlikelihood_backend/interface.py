"""Simplified Likelihood Interface"""

from typing import Optional, Text, Callable, List, Union, Tuple
from autograd import numpy as np

from spey.optimizer import fit
from spey.base import BackendBase
from spey.utils import ExpectationType
from spey._version import __version__
from .sldata import SLData, expansion_output
from .operators import logpdf, hessian_logpdf_func, objective_wrapper
from .sampler import sample_generator

__all__ = ["SimplifiedLikelihoodInterface"]

# pylint: disable=E1101


class SimplifiedLikelihoodInterface(BackendBase):
    """
    Simplified Likelihood Interface.

    Args:
        signal_yields (``np.ndarray``): signal yields
        background_yields (``np.ndarray``): background yields
        data (``np.ndarray``): observed yields
        covariance_matrix (``np.ndarray``): covariance matrix. The dimensionality of each axis has
          to match with ``background_yields``, ``signal_yields``, and ``data`` inputs.

          .. warning::

            The diagonal terms of the covariance matrix involves squared absolute background
            uncertainties. In case of uncorralated bins user should provide a diagonal matrix
            with squared background uncertainties.

        delta_sys (``float``, default ``0.0``): systematic uncertainty on signal.
        third_moment (``np.ndarray``, default ``None``): third moment for skewed gaussian.
          See eqs. 3.10, 3.11, 3.12, 3.13 in :xref:`1809.05548` for details.

    .. note::

        To enable a differentiable statistical model, all inputs are wrapped with
        :func:`autograd.numpy.array` function.
    """

    name: Text = "simplified_likelihoods"
    """Name of the backend"""
    version: Text = __version__
    """Version of the backend"""
    author: Text = "SpeysideHEP"
    """Author of the backend"""
    spey_requires: Text = __version__
    """Spey version required for the backend"""
    doi: List[Text] = ["10.1007/JHEP04(2019)064"]
    """Citable DOI for the backend"""
    arXiv: List[Text] = ["1809.05548"]
    """arXiv reference for the backend"""

    __slots__ = ["_model", "_third_moment_expansion"]

    def __init__(
        self,
        signal_yields: np.ndarray,
        background_yields: np.ndarray,
        data: np.ndarray,
        covariance_matrix: np.ndarray,
        delta_sys: float = 0.0,
        third_moment: Optional[np.ndarray] = None,
    ):
        self._model = SLData(
            observed=np.array(data, dtype=np.float64),
            signal=np.array(signal_yields, dtype=np.float64),
            background=np.array(background_yields, dtype=np.float64),
            covariance=np.array(covariance_matrix, dtype=np.float64),
            delta_sys=delta_sys,
            third_moment=np.array(third_moment, dtype=np.float64)
            if third_moment
            else None,
            name="sl_model",
        )
        self._third_moment_expansion: Optional[expansion_output] = None

    @property
    def model(self) -> SLData:
        """
        Accessor to the model container.

        Returns:
            ~spey.backends.simplifiedlikelihood_backend.sldata.SLData:
            Data container object that inherits :obj:`~spey.DataBase`.
        """
        return self._model

    @property
    def third_moment_expansion(self) -> expansion_output:
        """Get third moment expansion"""
        if self._third_moment_expansion is None:
            self._third_moment_expansion = self.model.compute_expansion()
        return self._third_moment_expansion

    def get_objective_function(
        self,
        expected: ExpectationType = ExpectationType.observed,
        data: Optional[np.ndarray] = None,
        do_grad: bool = True,
    ) -> Callable[[np.ndarray], Union[Tuple[float, np.ndarray], float]]:
        r"""
        Objective function i.e. twice negative log-likelihood, :math:`-2\log\mathcal{L}(\mu, \theta)`

        Args:
            expected (~spey.ExpectationType): Sets which values the fitting algorithm should focus and
              p-values to be computed.

              * :obj:`~spey.ExpectationType.observed`: Computes the p-values with via post-fit
                prescriotion which means that the experimental data will be assumed to be the truth
                (default).
              * :obj:`~spey.ExpectationType.aposteriori`: Computes the expected p-values with via
                post-fit prescriotion which means that the experimental data will be assumed to be
                the truth.
              * :obj:`~spey.ExpectationType.apriori`: Computes the expected p-values with via pre-fit
                prescription which means that the SM will be assumed to be the truth.
            data (``np.ndarray``, default ``None``): input data that to fit
            do_grad (``bool``, default ``True``): If ``True`` return objective and its gradient
              as ``tuple`` if ``False`` only returns objective function.

        Returns:
            ``Callable[[np.ndarray], Union[float, Tuple[float, np.ndarray]]]``:
            Function which takes fit parameters (:math:`\mu` and :math:`\theta`) and returns either
            objective or objective and its gradient.
        """
        current_model: SLData = (
            self.model
            if expected != ExpectationType.apriori
            else self.model.expected_dataset
        )

        return objective_wrapper(
            signal=current_model.signal,
            background=current_model.background,
            data=data if data is not None else current_model.observed,
            third_moment_expansion=self.third_moment_expansion,
            do_grad=do_grad,
        )

    def get_logpdf_func(
        self,
        expected: ExpectationType = ExpectationType.observed,
        data: Optional[np.array] = None,
    ) -> Callable[[np.ndarray, np.ndarray], float]:
        r"""
        Generate function to compute :math:`\log\mathcal{L}(\mu, \theta)` where :math:`\mu` is the
        parameter of interest and :math:`\theta` are nuisance parameters.

        Args:
            expected (~spey.ExpectationType): Sets which values the fitting algorithm should focus and
              p-values to be computed.

              * :obj:`~spey.ExpectationType.observed`: Computes the p-values with via post-fit
                prescriotion which means that the experimental data will be assumed to be the truth
                (default).
              * :obj:`~spey.ExpectationType.aposteriori`: Computes the expected p-values with via
                post-fit prescriotion which means that the experimental data will be assumed to be
                the truth.
              * :obj:`~spey.ExpectationType.apriori`: Computes the expected p-values with via pre-fit
                prescription which means that the SM will be assumed to be the truth.
            data (``np.array``, default ``None``): input data that to fit

        Returns:
            ``Callable[[np.ndarray], float]``:
            Function that takes fit parameters (:math:`\mu` and :math:`\theta`) and computes
            :math:`\log\mathcal{L}(\mu, \theta)`.
        """
        current_model: SLData = (
            self.model
            if expected != ExpectationType.apriori
            else self.model.expected_dataset
        )
        return lambda pars: logpdf(
            pars=pars,
            signal=current_model.signal,
            background=current_model.background,
            observed=data or current_model.observed,
            third_moment_expansion=self.third_moment_expansion,
        )

    def get_hessian_logpdf_func(
        self,
        expected: ExpectationType = ExpectationType.observed,
        data: Optional[np.ndarray] = None,
    ) -> Callable[[np.ndarray], float]:
        r"""
        Currently Hessian of :math:`\log\mathcal{L}(\mu, \theta)` is only used to compute
        variance on :math:`\mu`. This method returns a callable function which takes fit
        parameters (:math:`\mu` and :math:`\theta`) and returns Hessian.

        Args:
            expected (~spey.ExpectationType): Sets which values the fitting algorithm should focus and
              p-values to be computed.

              * :obj:`~spey.ExpectationType.observed`: Computes the p-values with via post-fit
                prescriotion which means that the experimental data will be assumed to be the truth
                (default).
              * :obj:`~spey.ExpectationType.aposteriori`: Computes the expected p-values with via
                post-fit prescriotion which means that the experimental data will be assumed to be
                the truth.
              * :obj:`~spey.ExpectationType.apriori`: Computes the expected p-values with via pre-fit
                prescription which means that the SM will be assumed to be the truth.
            data (``np.ndarray``, default ``None``): input data that to fit

        Returns:
            ``Callable[[np.ndarray], float]``:
            Function that takes fit parameters (:math:`\mu` and :math:`\theta`) and
            returns Hessian of :math:`\log\mathcal{L}(\mu, \theta)`.
        """
        current_model: SLData = (
            self.model
            if expected != ExpectationType.apriori
            else self.model.expected_dataset
        )

        hess = hessian_logpdf_func(
            current_model.signal, current_model.background, self.third_moment_expansion
        )

        return lambda pars: hess(pars, data or current_model.observed)

    def get_sampler(self, pars: np.ndarray) -> Callable[[int], np.ndarray]:
        r"""
        Retreives the function to sample from.

        Args:
            pars (``np.ndarray``): fit parameters (:math:`\mu` and :math:`\theta`)

        Returns:
            ``Callable[[int], np.ndarray]``:
            Function that takes ``number_of_samples`` as input and draws as many samples
            from the statistical model.
        """
        return sample_generator(
            pars=pars,
            signal=self.model.signal,
            background=self.model.background,
            third_moment_expansion=self.third_moment_expansion,
        )

    def generate_asimov_data(
        self,
        expected: ExpectationType = ExpectationType.observed,
        test_statistics: Text = "qtilde",
        **kwargs,
    ) -> np.ndarray:
        r"""
        Backend specific method to generate Asimov data.

        Args:
            expected (~spey.ExpectationType): Sets which values the fitting algorithm should focus and
              p-values to be computed.

              * :obj:`~spey.ExpectationType.observed`: Computes the p-values with via post-fit
                prescriotion which means that the experimental data will be assumed to be the truth
                (default).
              * :obj:`~spey.ExpectationType.aposteriori`: Computes the expected p-values with via
                post-fit prescriotion which means that the experimental data will be assumed to be
                the truth.
              * :obj:`~spey.ExpectationType.apriori`: Computes the expected p-values with via pre-fit
                prescription which means that the SM will be assumed to be the truth.

            test_statistics (``Text``, default ``"qtilde"``): test statistics.

              * ``'qtilde'``: (default) performs the calculation using the alternative test statistic,
                :math:`\tilde{q}_{\mu}`, see eq. (62) of :xref:`1007.1727`
                (:func:`~spey.hypothesis_testing.test_statistics.qmu_tilde`).

                .. warning::

                    Note that this assumes that :math:`\hat\mu\geq0`, hence ``allow_negative_signal``
                    assumed to be ``False``. If this function has been executed by user, ``spey``
                    assumes that this is taken care of throughout the external code consistently.
                    Whilst computing p-values or upper limit on :math:`\mu` through ``spey`` this
                    is taken care of automatically in the backend.

              * ``'q'``: performs the calculation using the test statistic :math:`q_{\mu}`, see
                eq. (54) of :xref:`1007.1727` (:func:`~spey.hypothesis_testing.test_statistics.qmu`).
              * ``'q0'``: performs the calculation using the discovery test statistic, see eq. (47)
                of :xref:`1007.1727` :math:`q_{0}` (:func:`~spey.hypothesis_testing.test_statistics.q0`).

            kwargs: keyword arguments for the optimiser.

        Returns:
            ``Union[List[float], np.ndarray]``:
            Asimov data.
        """
        model: SLData = (
            self.model
            if expected != ExpectationType.apriori
            else self.model.expected_dataset
        )

        # Do not allow asimov data to be negative!
        par_bounds = [(0.0, 1.0)] + [
            (-1 * (bkg + sig * (test_statistics == "q0")), 100.0)
            for sig, bkg in zip(model.signal, model.background)
        ]

        func = objective_wrapper(
            signal=model.signal,
            background=model.background,
            data=model.observed,
            third_moment_expansion=self.third_moment_expansion,
            do_grad=True,
        )

        _, fit_pars = fit(
            func=func,
            model_configuration=model.config(
                allow_negative_signal=test_statistics in ["q", "qmu"]
            ),
            do_grad=True,
            fixed_poi_value=1.0 if test_statistics == "q0" else 0.0,
            bounds=par_bounds,
            **kwargs,
        )

        return model.background + fit_pars[1:]
