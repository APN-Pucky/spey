import numpy as np
from typing import Tuple, Union

from madstats.utils import ExpectationType

__all__ = ["Recorder"]


class Recorder:
    """
    Class for recording likelihood evolution of the statistical model. If the recorder is on,
    repetative values will not be computed and will be automatically extracted from the recorder.
    Recorder can be turned on and off globally using the following;

    .. code-block:: python3

        Recorder.turn_off() # turn recorder off globally
        Recorder.turn_on() # turn recorder on globally

    By default, recorder is off, but it still records all the computations held by each statistical
    model. It will only use these values when the recorder is turned on.
    """
    RECORD = False

    def __init__(self):
        # Record style:
        # _poi_test_record
        # Expectation type : { poi test : nll value}
        # _maximum_likelihood_record
        # Expectation type : ( poi test , nll value)
        self._poi_test_record = {
            str(ExpectationType.observed): {},
            str(ExpectationType.aposteriori): {},
            str(ExpectationType.apriori): {},
        }
        self._maximum_likelihood_record = {
            str(ExpectationType.observed): False,
            str(ExpectationType.aposteriori): False,
            str(ExpectationType.apriori): False,
        }

    @staticmethod
    def turn_off() -> None:
        """Turn off switch"""
        Recorder.RECORD = False

    @staticmethod
    def turn_on() -> None:
        """Turn on switch"""
        Recorder.RECORD = True

    @staticmethod
    def is_on() -> bool:
        return Recorder.RECORD

    def get_poi_test(self, expected: ExpectationType, poi_test: float) -> Union[float, bool]:
        """Retrieve NLL value for given poi test and expectation value"""
        poi_test = np.float32(poi_test)
        if self.is_on():
            return self._poi_test_record[str(expected)].get(poi_test, False)
        else:
            return False

    def get_maximum_likelihood(self, expected: ExpectationType) -> Union[Tuple[float, float], bool]:
        """Retrieve maximum likelihood and fit param"""
        if self.is_on():
            return self._maximum_likelihood_record[str(expected)]
        else:
            return False

    def record_poi_test(
        self, expected: ExpectationType, poi_test: float, negative_loglikelihood: float
    ) -> None:
        poi_test = np.float32(poi_test)
        negative_loglikelihood = np.float32(negative_loglikelihood)
        self._poi_test_record[str(expected)].update({poi_test: negative_loglikelihood})

    def record_maximum_likelihood(
        self, expected: ExpectationType, poi_test: float, negative_loglikelihood: float
    ) -> None:
        poi_test = np.float32(poi_test)
        negative_loglikelihood = np.float32(negative_loglikelihood)

        record = True
        if self.get_maximum_likelihood(expected) is not False:
            if self.get_maximum_likelihood(expected)[1] < negative_loglikelihood:
                record = False
        if record:
            self._maximum_likelihood_record[str(expected)] = (poi_test, negative_loglikelihood)