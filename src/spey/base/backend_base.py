"""Abstract Methods for backend objects"""

from abc import ABC, abstractmethod
from typing import Text, Tuple, Callable, Union, List, Optional

import numpy as np

from spey.utils import ExpectationType
from .model_config import ModelConfig


__all__ = ["BackendBase", "DataBase"]


class DataBase(ABC):
    """
    An abstract class construction to enforce certain behaviour on statistical model data space.
    Each backend requires different ways of data embedding, while simple ``numpy`` arrays are
    possiblitiy, in order to track different error sources, different backends have been developed
    with different data structures. In order to perform certain computations, ``spey`` needs to
    have access to specific information regarding the data. Hence, each data hanler object of any
    backend is required to inherit :obj:`~spey.DataBase`.
    """

    @property
    @abstractmethod
    def minimum_poi(self) -> float:
        r"""
        Retreive minimum value that :math:`\mu` can take. This will limit the span of the scan
        and ensures that :math:`N^{\rm bkg} + \mu N^{\rm sig} \geq 0`.

        Returns:
            :obj:`float`:
            :math:`\min\left(\frac{N^{\rm bkg}_i}{N^{\rm sig}_i}\right)\ ,\ i\in {\rm bins}`
        """
        # This method must be casted as property

    @property
    @abstractmethod
    def isAlive(self) -> bool:
        """Returns True if at least one bin has non-zero signal yield."""
        # This method has to be a property

    @abstractmethod
    def config(
        self, allow_negative_signal: bool = True, poi_upper_bound: float = 40.0
    ) -> ModelConfig:
        r"""
        Model configuration.

        Args:
            allow_negative_signal (:obj:`bool`, default :obj:`True`): If :obj:`True` :math:`\hat\mu`
              value will be allowed to be negative.
            poi_upper_bound (:obj:`float`, default :obj:`40.0`): upper bound for parameter of interest,
              :math:`\mu`.

        Returns:
            ~spey.base.ModelConfig:
            Model configuration. Information regarding the position of POI in parameter list, suggested
            input and bounds.
        """


class BackendBase(ABC):
    """
    An abstract class construction to enforce certain behaviour on statistical model backend.
    In order to perform certain computations, ``spey`` needs to have access to specific
    function constructions such as precsription to form likelihood. Hence, each backend is
    required to inherit :obj:`~spey.BackendBase`.
    """

    @property
    @abstractmethod
    def model(self) -> DataBase:
        """
        Accessor to the model container.

        Returns:
            ~spey.DataBase:
            Data container object that inherits :obj:`~spey.DataBase`.
        """
        # This method must be casted as property

    @abstractmethod
    def get_logpdf_func(
        self,
        expected: ExpectationType = ExpectationType.observed,
        data: Optional[Union[List[float], np.ndarray]] = None,
    ) -> Callable[[np.ndarray], float]:
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
            data (:obj:`Union[List[float], np.ndarray]`, default :obj:`None`): input data that to fit

        Returns:
            :obj:`Callable[[np.ndarray], float]`:
            Function that takes fit parameters (:math:`\mu` and :math:`\theta`) and computes
            :math:`\log\mathcal{L}(\mu, \theta)`.
        """

    @abstractmethod
    def get_objective_function(
        self,
        expected: ExpectationType = ExpectationType.observed,
        data: Optional[Union[List[float], np.ndarray]] = None,
        do_grad: bool = True,
    ) -> Callable[[np.ndarray], Union[float, Tuple[float, np.ndarray]]]:
        r"""
        Objective function is the function to perform the optimisation on. This function is
        expected to be twice negative log-likelihood, :math:`-2\log\mathcal{L}(\mu, \theta)`.
        Additionally, if available it canbe bundled with the gradient of twice negative log-likelihood.

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
            data (:obj:`Union[List[float], np.ndarray]`, default :obj:`None`): input data that to fit
            do_grad (:obj:`bool`, default :obj:`True`): If ``True`` return objective and its gradient
              as ``tuple`` (subject to availablility) if ``False`` only returns objective function.

        Returns:
            :obj:`Callable[[np.ndarray], Union[float, Tuple[float, np.ndarray]]]`:
            Function which takes fit parameters (:math:`\mu` and :math:`\theta`) and returns either
            objective or objective and its gradient.
        """

    def get_hessian_logpdf_func(
        self,
        expected: ExpectationType = ExpectationType.observed,
        data: Optional[Union[List[float], np.ndarray]] = None,
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
            data (:obj:`Union[List[float], np.ndarray]`, default :obj:`None`): input data that to fit

        Raises:
            :obj:`NotImplementedError`: If the Hessian of the backend has not been implemented.

        Returns:
            :obj:`Callable[[np.ndarray], float]`:
            Function that takes fit parameters (:math:`\mu` and :math:`\theta`) and
            returns Hessian of :math:`\log\mathcal{L}(\mu, \theta)`.
        """
        raise NotImplementedError("This method has not been implemented")

    def get_sampler(self, pars: np.ndarray) -> Callable[[int], np.ndarray]:
        r"""
        Retreives the function to sample from.

        Args:
            pars (:obj:`np.ndarray`): fit parameters (:math:`\mu` and :math:`\theta`)

        Raises:
            :obj:`NotImplementedError`: If the sampler for the backend has not been implemented.

        Returns:
            :obj:`Callable[[int], np.ndarray]`:
            Function that takes ``number_of_samples`` as input and draws as many samples
            from the statistical model.
        """
        raise NotImplementedError("This method has not been implemented")

    @abstractmethod
    def generate_asimov_data(
        self,
        expected: ExpectationType = ExpectationType.observed,
        test_statistics: Text = "qtilde",
        **kwargs,
    ) -> Union[List[float], np.ndarray]:
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

            test_statistics (:obj:`Text`, default :obj:`"qtilde"`): test statistics.

              * ``'qtilde'``: (default) performs the calculation using the alternative test statistic,
                :math:`\tilde{q}_{\mu}`, see eq. (62) of :xref:`1007.1727`
                (:func:`~spey.hypothesis_testing.test_statistics.qmu_tilde`).

                .. warning::

                    Note that this assumes that :math:`\hat\mu\geq0`, hence :obj:`allow_negative_signal`
                    assumed to be :obj:`False`. If this function has been executed by user, :obj:`spey`
                    assumes that this is taken care of throughout the external code consistently.
                    Whilst computing p-values or upper limit on :math:`\mu` through :obj:`spey` this
                    is taken care of automatically in the backend.

              * ``'q'``: performs the calculation using the test statistic :math:`q_{\mu}`, see
                eq. (54) of :xref:`1007.1727` (:func:`~spey.hypothesis_testing.test_statistics.qmu`).
              * ``'q0'``: performs the calculation using the discovery test statistic, see eq. (47)
                of :xref:`1007.1727` :math:`q_{0}` (:func:`~spey.hypothesis_testing.test_statistics.q0`).

            kwargs: keyword arguments for the optimiser.

        Returns:
            :obj:`Union[List[float], np.ndarray]`:
            Asimov data.
        """

    def negative_loglikelihood(
        self, poi_test: float = 1.0, expected: ExpectationType = ExpectationType.observed, **kwargs
    ) -> Tuple[float, np.ndarray]:
        r"""
        Backend specific method to compute negative log-likelihood for a parameter of interest
        :math:`\mu`.

        .. note::

            Interface first calls backend specific methods to compute likelihood. If they are not
            implemented, it optimizes objective function through ``spey`` interface. Either prescription
            to optimizing the likelihood or objective function must be available for a backend to
            be sucessfully integrated to the ``spey`` interface.

        Args:
            poi_test (:obj:`float`, default :obj:`1.0`): parameter of interest, :math:`\mu`.
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

            kwargs: keyword arguments for the optimiser.

        Raises:
            :obj:`NotImplementedError`: If the method is not available for the backend.

        Returns:
            :obj:`Tuple[float, np.ndarray]`:
            value of negative log-likelihood at POI of interest and fit parameters
            (:math:`\mu` and :math:`\theta`).
        """
        raise NotImplementedError("This method has not been implemented")

    def asimov_negative_loglikelihood(
        self,
        poi_test: float = 1.0,
        expected: ExpectationType = ExpectationType.observed,
        test_statistics: Text = "qtilde",
        **kwargs,
    ) -> Tuple[float, np.ndarray]:
        r"""
        Compute negative log-likelihood at fixed :math:`\mu` for Asimov data.

        .. note::

            Interface first calls backend specific methods to compute likelihood. If they are not
            implemented, it optimizes objective function through ``spey`` interface. Either prescription
            to optimizing the likelihood or objective function must be available for a backend to
            be sucessfully integrated to the ``spey`` interface.

        Args:
            poi_test (:obj:`float`, default :obj:`1.0`): parameter of interest, :math:`\mu`.
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

            test_statistics (:obj:`Text`, default :obj:`"qtilde"`): test statistics.

              * ``'qtilde'``: (default) performs the calculation using the alternative test statistic,
                :math:`\tilde{q}_{\mu}`, see eq. (62) of :xref:`1007.1727`
                (:func:`~spey.hypothesis_testing.test_statistics.qmu_tilde`).

                .. warning::

                    Note that this assumes that :math:`\hat\mu\geq0`, hence :obj:`allow_negative_signal`
                    assumed to be :obj:`False`. If this function has been executed by user, :obj:`spey`
                    assumes that this is taken care of throughout the external code consistently.
                    Whilst computing p-values or upper limit on :math:`\mu` through :obj:`spey` this
                    is taken care of automatically in the backend.

              * ``'q'``: performs the calculation using the test statistic :math:`q_{\mu}`, see
                eq. (54) of :xref:`1007.1727` (:func:`~spey.hypothesis_testing.test_statistics.qmu`).
              * ``'q0'``: performs the calculation using the discovery test statistic, see eq. (47)
                of :xref:`1007.1727` :math:`q_{0}` (:func:`~spey.hypothesis_testing.test_statistics.q0`).

            kwargs: keyword arguments for the optimiser.

        Raises:
            :obj:`NotImplementedError`: If the method is not available for the backend.

        Returns:
            :obj:`Tuple[float, np.ndarray]`:
            value of negative log-likelihood at POI of interest and fit parameters
            (:math:`\mu` and :math:`\theta`).
        """
        raise NotImplementedError("This method has not been implemented")

    def minimize_negative_loglikelihood(
        self,
        expected: ExpectationType = ExpectationType.observed,
        allow_negative_signal: bool = True,
        **kwargs,
    ) -> Tuple[float, np.ndarray]:
        r"""
        A backend specific method to minimize negative log-likelihood.

        .. note::

            Interface first calls backend specific methods to compute likelihood. If they are not
            implemented, it optimizes objective function through ``spey`` interface. Either prescription
            to optimizing the likelihood or objective function must be available for a backend to
            be sucessfully integrated to the ``spey`` interface.

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

            allow_negative_signal (:obj:`bool`, default :obj:`True`): If :obj:`True` :math:`\hat\mu`
              value will be allowed to be negative.
            kwargs: keyword arguments for the optimiser.

        Raises:
            :obj:`NotImplementedError`: If the method is not available for the backend.

        Returns:
            :obj:`Tuple[float, np.ndarray]`:
            value of negative log-likelihood and fit parameters (:math:`\mu` and :math:`\theta`).
        """
        raise NotImplementedError("This method has not been implemented")

    def minimize_asimov_negative_loglikelihood(
        self,
        expected: ExpectationType = ExpectationType.observed,
        test_statistics: Text = "qtilde",
        **kwargs,
    ) -> Tuple[float, np.ndarray]:
        r"""
        A backend specific method to minimize negative log-likelihood for Asimov data.

        .. note::

            Interface first calls backend specific methods to compute likelihood. If they are not
            implemented, it optimizes objective function through ``spey`` interface. Either prescription
            to optimizing the likelihood or objective function must be available for a backend to
            be sucessfully integrated to the ``spey`` interface.

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

            test_statistics (:obj:`Text`, default :obj:`"qtilde"`): test statistics.

              * ``'qtilde'``: (default) performs the calculation using the alternative test statistic,
                :math:`\tilde{q}_{\mu}`, see eq. (62) of :xref:`1007.1727`
                (:func:`~spey.hypothesis_testing.test_statistics.qmu_tilde`).

                .. warning::

                    Note that this assumes that :math:`\hat\mu\geq0`, hence :obj:`allow_negative_signal`
                    assumed to be :obj:`False`. If this function has been executed by user, :obj:`spey`
                    assumes that this is taken care of throughout the external code consistently.
                    Whilst computing p-values or upper limit on :math:`\mu` through :obj:`spey` this
                    is taken care of automatically in the backend.

              * ``'q'``: performs the calculation using the test statistic :math:`q_{\mu}`, see
                eq. (54) of :xref:`1007.1727` (:func:`~spey.hypothesis_testing.test_statistics.qmu`).
              * ``'q0'``: performs the calculation using the discovery test statistic, see eq. (47)
                of :xref:`1007.1727` :math:`q_{0}` (:func:`~spey.hypothesis_testing.test_statistics.q0`).

            kwargs: keyword arguments for the optimiser.

        Raises:
            :obj:`NotImplementedError`: If the method is not available for the backend.

        Returns:
            :obj:`Tuple[float, np.ndarray]`:
            value of negative log-likelihood and fit parameters (:math:`\mu` and :math:`\theta`).
        """
        raise NotImplementedError("This method has not been implemented")
