import math

from wake.testing import *
from wake.testing.fuzzing import random_int

from pytypes.tests.InterestRatesMock import InterestRatesMock


@default_chain.connect()
def test_interest_rates():
    default_chain.set_default_accounts(default_chain.accounts[0])

    mock = InterestRatesMock.deploy()
    max_diff = 0
    params = ()

    for _ in range(100_000):
        interest_rate_period = random_int(1, 90 * 24 * 60 * 60)  # 1 second to 90 days
        fixed_interest_rate_wad = random_int(1 * 10 ** 15, 100 * 10 ** 15)  # 0.1% to 10%
        notional_wad = 100_000 * 10 ** 18
        x = mock.addContinuousCompoundInterestUsingRatePeriodMultiplication(
            notional_wad, fixed_interest_rate_wad * interest_rate_period
        )
        y = notional_wad / 10 ** 18 * math.exp(fixed_interest_rate_wad / 10 ** 18 * interest_rate_period / (365 * 24 * 60 * 60))

        diff = abs(x / 10 ** 18 - y)
        if diff > max_diff:
            params = (interest_rate_period, fixed_interest_rate_wad, notional_wad)
            max_diff = diff
            print(f"New max diff: {diff}, {x / 10 ** 18}, {y}")
