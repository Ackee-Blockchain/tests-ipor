import pytest

from wake.testing import *
from wake.testing.fuzzing import random_int
from pytypes.source.contracts.interfaces.IStrategy import IStrategy
from pytypes.source.contracts.interfaces.IStrategyCompound import IStrategyCompound
from pytypes.source.contracts.vault.strategies.StrategyCompound import StrategyCompound
from pytypes.source.contracts.vault.interfaces.compound.CErc20 import CErc20
from pytypes.source.contracts.vault.interfaces.compound.Comptroller import Comptroller
from pytypes.openzeppelin.contracts.token.ERC20.extensions.IERC20Metadata import IERC20Metadata
from .config import FORK_URL
from .utils import deploy_with_proxy


@pytest.fixture
def setup_compound_dai_fixture():
    with default_chain.connect(fork=FORK_URL):
        yield setup_compound_dai()


def setup_compound_dai():
    a = default_chain.accounts[0]
    default_chain.set_default_accounts(a)

    dai = IERC20Metadata("0x6B175474E89094C44Da98b954EedeAC495271d0F")
    assert dai.symbol() == "DAI"

    compound_strategy = deploy_with_proxy(StrategyCompound)
    cdai = CErc20("0x5d3a536e4d6dbd6114cc1ead35777bab948e3643")
    comptroller = Comptroller("0x3d9819210a31b4961b30ef54be2aed79b9c9cd3b")
    comp_erc20 = IERC20Metadata("0xc00e94cb662c3520282e6f5717214004a7f26888")
    compound_strategy.initialize(dai, cdai, comptroller, comp_erc20)

    # mock "mint"
    dai.transfer(a, 10**23, from_="0x075e72a5eDf65F0A5f44699c7654C1a76941Ddc8")

    return compound_strategy, cdai, dai, comp_erc20, comptroller


@pytest.fixture
def setup_compound_usdc_fixture():
    with default_chain.connect(fork=FORK_URL):
        yield setup_compound_usdc()


def setup_compound_usdc():
    a = default_chain.accounts[0]
    default_chain.set_default_accounts(a)

    usdc = IERC20Metadata("0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48")
    assert usdc.symbol() == "USDC"

    compound_strategy = deploy_with_proxy(StrategyCompound)
    cusdc = CErc20("0x39aa39c021dfbae8fac545936693ac917d5e7563")
    comptroller = Comptroller("0x3d9819210a31b4961b30ef54be2aed79b9c9cd3b")
    comp_erc20 = IERC20Metadata("0xc00e94cb662c3520282e6f5717214004a7f26888")
    compound_strategy.initialize(usdc, cusdc, comptroller, comp_erc20)

    # mock "mint"
    usdc.transfer(a, 10**12, from_="0xcEe284F754E854890e311e3280b767F80797180d")

    return compound_strategy, cusdc, usdc, comp_erc20, comptroller


@pytest.fixture
def setup_compound_usdt_fixture():
    with default_chain.connect(fork=FORK_URL):
        yield setup_compound_usdt()


def setup_compound_usdt():
    a = default_chain.accounts[0]
    default_chain.set_default_accounts(a)

    usdt = IERC20Metadata("0xdac17f958d2ee523a2206206994597c13d831ec7")
    assert usdt.symbol() == "USDT"

    compound_strategy = deploy_with_proxy(StrategyCompound)
    cusdt = CErc20("0xf650c3d88d12db855b8bf7d11be6c55a4e07dcc9")
    comptroller = Comptroller("0x3d9819210a31b4961b30ef54be2aed79b9c9cd3b")
    comp_erc20 = IERC20Metadata("0xc00e94cb662c3520282e6f5717214004a7f26888")
    compound_strategy.initialize(usdt, cusdt, comptroller, comp_erc20)

    # mock "mint"
    usdt.transfer(a, 10**12, from_="0x47ac0Fb4F2D84898e4D9E7b4DaB3C24507a6D503")

    return compound_strategy, cusdt, usdt, comp_erc20, comptroller


def test_compound_core(setup_compound_dai_fixture):
    compound_strategy, cdai, dai, _, _ = setup_compound_dai_fixture
    assert isinstance(compound_strategy, StrategyCompound)
    assert isinstance(cdai, CErc20)

    a = default_chain.accounts[0]
    b = default_chain.accounts[1]

    assert compound_strategy.getAsset() == dai.address
    assert compound_strategy.getShareToken() == cdai.address
    assert compound_strategy.getAssetManagement() == Address.ZERO
    assert compound_strategy.getTreasuryManager() == a.address
    assert compound_strategy.getTreasury() == Address.ZERO

    with must_revert(Error("Ownable: caller is not the owner")):
        compound_strategy.setAssetManagement(b, from_=b)

    with must_revert(Error("Ownable: caller is not the owner")):
        compound_strategy.setTreasuryManager(b, from_=b)

    with must_revert(Error("IPOR_505")):
        compound_strategy.setTreasury(b, from_=b)

    tx = compound_strategy.setAssetManagement(b, from_=a)
    assert IStrategy.AssetManagementChanged(b.address) in tx.events
    assert compound_strategy.getAssetManagement() == b.address

    tx = compound_strategy.setTreasuryManager(b, from_=a)
    assert IStrategy.TreasuryManagerChanged(b.address) in tx.events
    assert compound_strategy.getTreasuryManager() == b.address

    with must_revert(Error("IPOR_505")):
        compound_strategy.setTreasury(b, from_=a)

    tx = compound_strategy.setTreasury(b, from_=b)
    assert IStrategy.TreasuryChanged(b.address) in tx.events
    assert compound_strategy.getTreasury() == b.address


def test_compound_apr(setup_compound_dai_fixture):
    compound_strategy, cdai, _, _, _ = setup_compound_dai_fixture
    assert isinstance(compound_strategy, StrategyCompound)
    assert isinstance(cdai, CErc20)

    max_rel_error = 0
    max_rel_error_blocks_per_day = 0
    for _ in range(100):
        blocks_per_day = random_int(5_000, 500_000)
        tx = compound_strategy.setBlocksPerDay(blocks_per_day)
        assert tx.events == [IStrategyCompound.BlocksPerDayChanged(blocks_per_day)]
        computed_apr = ((((cdai.supplyRatePerBlock() / 10 ** 18 * blocks_per_day + 1) ** 365)) - 1) * 10 ** 18

        rel_error = abs(compound_strategy.getApy() - computed_apr) / computed_apr

        if rel_error > max_rel_error:
            max_rel_error_blocks_per_day = blocks_per_day
            max_rel_error = rel_error

    print(f"StrategyCompound.getApr max relative error: {max_rel_error * 100}% with blocks_per_day={max_rel_error_blocks_per_day}")


def div_round(a, b):
    return (a + b // 2) // b


@pytest.mark.parametrize("setup_compound", ["setup_compound_dai_fixture", "setup_compound_usdc_fixture", "setup_compound_usdt_fixture"])
def test_compound_deposit_withdraw(setup_compound, request):
    compound_strategy, casset, asset, comp, comptroller = request.getfixturevalue(setup_compound)
    assert isinstance(compound_strategy, StrategyCompound)
    assert isinstance(casset, CErc20)
    assert isinstance(asset, IERC20Metadata)
    assert isinstance(comptroller, Comptroller)

    a = default_chain.accounts[0]
    compound_strategy.setAssetManagement(a)
    assert compound_strategy.balanceOf() == 0

    deposited_amount = random_int(10_000, 100_000) * (10 ** asset.decimals())
    assert asset.balanceOf(a) >= deposited_amount

    asset.approve(compound_strategy, deposited_amount)
    # convert deposited_amount to wads
    compound_strategy.deposit(deposited_amount * 10 ** (18 - asset.decimals()))

    # should receive deposited_amount // exchangeRateStored
    assert (deposited_amount * 10 ** 18) // casset.exchangeRateStored() == casset.balanceOf(compound_strategy)

    # burn remaining balance
    asset.transfer(Address(1), asset.balanceOf(a), from_=a)

    # error can be up to 1 because of rounding
    assert abs(compound_strategy.balanceOf() - (casset.balanceOf(compound_strategy) * casset.exchangeRateStored() // 10 ** asset.decimals())) <= 1

    # withdraw half
    balance = compound_strategy.balanceOf()
    casset_balance = casset.balanceOf(compound_strategy)

    half = balance // 2
    # have to follow the same rounding as in the contract
    casset_half = div_round(half // (10 ** (18 - asset.decimals())) * 10 ** 18, casset.exchangeRateStored())
    compound_strategy.withdraw(half)

    assert casset.balanceOf(compound_strategy) == casset_balance - casset_half
    assert asset.balanceOf(a) == casset_half * casset.exchangeRateStored() // 10 ** 18
    tmp = asset.balanceOf(a)

    # withdraw the rest
    casset_rest = div_round(compound_strategy.balanceOf() // (10 ** (18 - asset.decimals())) * 10 ** 18, casset.exchangeRateStored())
    compound_strategy.withdraw(compound_strategy.balanceOf())

    assert casset.balanceOf(compound_strategy) == casset_balance - casset_half - casset_rest
    assert asset.balanceOf(a) == tmp + casset_rest * casset.exchangeRateStored() // 10 ** 18

    assert comp.balanceOf(compound_strategy) == 0
    assert comp.balanceOf(a) == 0
    compound_strategy.setTreasury(a)
    tx = compound_strategy.doClaim()
    assert IStrategy.DoClaim(a.address, casset.address, a.address, comp.balanceOf(a)) in tx.events

    if comptroller.compSpeeds(casset) > 0:
        assert comptroller.balanceOf(a) > 0
