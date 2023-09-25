from pytypes.source.contracts.libraries.math.IporMath import IporMath
from pytypes.tests.MathMock import MathMock
from woke.testing import *

import random
import decimal

@default_chain.connect()
def test_division():
    default_chain.set_default_accounts(default_chain.accounts[0])
    IporMath.deploy()
    m = MathMock.deploy()
    for i in range(10**6):
        x1 = random.randint(1, 2**16)
        x2 = random.randint(1, 2**32)
        x3 = random.randint(1, 2**64)
        x4 = random.randint(1, 2**128)
        x5= random.randint(1, 2**256-1)
        y1 = random.randint(1, 2**8)
        y3 = random.randint(1, 2**16)
        y3 = random.randint(1, 2**32)
        y4 = random.randint(1, 2**64)
        y5 = random.randint(1, 2**128)
        x = random.choice([x1, x2, x3, x4, x5])
        y = random.choice([y1, y3, y3, y4, y5])

        decimal.getcontext().prec = 80
        z = m.division(x, y)
        assert z == (decimal.Decimal(x)/decimal.Decimal(y)).to_integral_value(rounding=decimal.ROUND_HALF_UP)
        assert z == (x + (y // 2)) // y


def div_int(a, b):
    q, r = divmod(a, b)
    return q + (2 * r // b)


@default_chain.connect()
def test_division_int():
    default_chain.set_default_accounts(default_chain.accounts[0])
    IporMath.deploy()
    m = MathMock.deploy()

    for _ in range(10**6):
        x1 = random.randint(-2**7, 2**7 - 1)
        x2 = random.randint(-2**15, 2**15 - 1)
        x3 = random.randint(-2**31, 2**31 - 1)
        x4 = random.randint(-2**63, 2**63 - 1)
        x5 = random.randint(-2**127, 2**127 - 1)
        x6 = random.randint(-2**255, 2**255 - 1)
        y1 = random.randint(-2**7, 2**7 - 1)
        y2 = random.randint(-2**15, 2**15 - 1)
        y3 = random.randint(-2**31, 2**31 - 1)
        y4 = random.randint(-2**63, 2**63 - 1)
        y5 = random.randint(-2**127, 2**127 - 1)
        y6 = random.randint(-2**255, 2**255 - 1)
        x = random.choice([x1, x2, x3, x4, x5, x6])
        y = random.choice([y1, y2, y3, y4, y5, y6])

        if y == 0:
            with must_revert(PanicCodeEnum.DIVISION_MODULO_BY_ZERO):
                m.divisionInt(x, y)
        else:
            assert m.divisionInt(x, y) == div_int(x, y)
