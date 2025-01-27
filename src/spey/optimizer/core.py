from typing import Callable, List, Tuple, Optional, Dict
import numpy as np

from spey.base.model_config import ModelConfig
from .scipy_tools import minimize


def fit(
    func: Callable[[np.ndarray], np.ndarray],
    model_configuration: ModelConfig,
    do_grad: bool = False,
    hessian: Optional[Callable[[np.ndarray], np.ndarray]] = None,
    initial_parameters: Optional[np.ndarray] = None,
    bounds: Optional[List[Tuple[float, float]]] = None,
    fixed_poi_value: Optional[float] = None,
    logpdf: Optional[Callable[[List[float]], float]] = None,
    constraints: Optional[List[Dict]] = None,
    **options,
) -> Tuple[float, np.ndarray]:

    init_pars = [*(initial_parameters or model_configuration.suggested_init)]
    par_bounds = [*(bounds or model_configuration.fixed_poi_bounds(fixed_poi_value))]

    constraints = constraints if constraints is not None else []
    if fixed_poi_value is not None:
        init_pars[model_configuration.poi_index] = fixed_poi_value
        constraints.append(
            {
                "type": "eq",
                "fun": lambda v: v[model_configuration.poi_index] - fixed_poi_value,
            }
        )

    options.update({"poi_index": model_configuration.poi_index})

    fun, x = minimize(
        func=func,
        init_pars=init_pars,
        do_grad=do_grad,
        hessian=hessian,
        bounds=par_bounds,
        constraints=constraints,
        **options,
    )

    return fun if logpdf is None else logpdf(x), x
