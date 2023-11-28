import pytest

from wake.testing import *
from wake.testing.fuzzing import random_int
from pytypes.source.contracts.interfaces.IStrategy import IStrategy
from pytypes.source.contracts.vault.interfaces.aave.AaveLendingPoolV2 import AaveLendingPoolV2
from pytypes.source.contracts.vault.strategies.StrategyAave import StrategyAave
from pytypes.source.contracts.vault.interfaces.aave.AaveLendingPoolProviderV2 import AaveLendingPoolProviderV2
from pytypes.source.contracts.vault.interfaces.aave.StakedAaveInterface import StakedAaveInterface
from pytypes.source.contracts.vault.interfaces.aave.AaveIncentivesInterface import AaveIncentivesInterface
from pytypes.openzeppelin.contracts.token.ERC20.extensions.IERC20Metadata import IERC20Metadata
from .config import FORK_URL
from .utils import deploy_with_proxy


@pytest.fixture
def setup_aave_dai_fixture():
    with default_chain.connect(fork=FORK_URL):
        yield setup_aave_dai()


def setup_aave_dai():
    a = default_chain.accounts[0]
    default_chain.set_default_accounts(a)

    dai = IERC20Metadata("0x6B175474E89094C44Da98b954EedeAC495271d0F")
    assert dai.symbol() == "DAI"

    aave_strategy = deploy_with_proxy(StrategyAave)
    adai = IERC20Metadata("0x028171bCA77440897B824Ca71D1c56caC55b68A3")
    lending_pool_provider = AaveLendingPoolProviderV2("0xB53C1a33016B2DC2fF3653530bfF1848a515c8c5")
    stk_aave = StakedAaveInterface("0x4da27a545c0c5B758a6BA100e3a049001de870f5")
    aave_incentives = AaveIncentivesInterface("0xd784927Ff2f95ba542BfC824c8a8a98F3495f6b5")
    aave_erc20 = IERC20Metadata("0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9")
    aave_strategy.initialize(dai, adai, lending_pool_provider, stk_aave, aave_incentives, aave_erc20)

    # mock "mint"
    dai.transfer(a, 10**23, from_="0x075e72a5eDf65F0A5f44699c7654C1a76941Ddc8")

    return aave_strategy, adai, dai, lending_pool_provider, aave_erc20, stk_aave, aave_incentives


@pytest.fixture
def setup_aave_usdc_fixture():
    with default_chain.connect(fork=FORK_URL):
        yield setup_aave_usdc()


def setup_aave_usdc():
    a = default_chain.accounts[0]
    default_chain.set_default_accounts(a)

    usdc = IERC20Metadata("0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48")
    assert usdc.symbol() == "USDC"

    aave_strategy = deploy_with_proxy(StrategyAave)
    ausdc = IERC20Metadata("0xBcca60bB61934080951369a648Fb03DF4F96263C")
    lending_pool_provider = AaveLendingPoolProviderV2("0xB53C1a33016B2DC2fF3653530bfF1848a515c8c5")
    stk_aave = StakedAaveInterface("0x4da27a545c0c5B758a6BA100e3a049001de870f5")
    aave_incentives = AaveIncentivesInterface("0xd784927Ff2f95ba542BfC824c8a8a98F3495f6b5")
    aave_erc20 = IERC20Metadata("0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9")
    aave_strategy.initialize(usdc, ausdc, lending_pool_provider, stk_aave, aave_incentives, aave_erc20)

    # mock "mint"
    usdc.transfer(a, 10**12, from_="0xcEe284F754E854890e311e3280b767F80797180d")

    return aave_strategy, ausdc, usdc, lending_pool_provider, aave_erc20, stk_aave, aave_incentives


@pytest.fixture
def setup_aave_usdt_fixture():
    with default_chain.connect(fork=FORK_URL):
        yield setup_aave_usdt()


def setup_aave_usdt():
    a = default_chain.accounts[0]
    default_chain.set_default_accounts(a)

    usdt = IERC20Metadata("0xdac17f958d2ee523a2206206994597c13d831ec7")
    assert usdt.symbol() == "USDT"

    aave_strategy = deploy_with_proxy(StrategyAave)
    ausdt = IERC20Metadata("0x3Ed3B47Dd13EC9a98b44e6204A523E766B225811")
    lending_pool_provider = AaveLendingPoolProviderV2("0xB53C1a33016B2DC2fF3653530bfF1848a515c8c5")
    stk_aave = StakedAaveInterface("0x4da27a545c0c5B758a6BA100e3a049001de870f5")
    aave_incentives = AaveIncentivesInterface("0xd784927Ff2f95ba542BfC824c8a8a98F3495f6b5")
    aave_erc20 = IERC20Metadata("0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9")
    aave_strategy.initialize(usdt, ausdt, lending_pool_provider, stk_aave, aave_incentives, aave_erc20)

    # mock "mint"
    usdt.transfer(a, 10**12, from_="0x47ac0Fb4F2D84898e4D9E7b4DaB3C24507a6D503")

    return aave_strategy, ausdt, usdt, lending_pool_provider, aave_erc20, stk_aave, aave_incentives


def test_aave_core(setup_aave_dai_fixture):
    aave_strategy, adai, dai, _, _, _, _ = setup_aave_dai_fixture
    assert isinstance(aave_strategy, StrategyAave)

    a = default_chain.accounts[0]
    b = default_chain.accounts[1]

    assert aave_strategy.getAsset() == dai.address
    assert aave_strategy.getShareToken() == adai.address
    assert aave_strategy.getAssetManagement() == Address.ZERO
    assert aave_strategy.getTreasuryManager() == a.address
    assert aave_strategy.getTreasury() == Address.ZERO

    with must_revert(Error("Ownable: caller is not the owner")):
        aave_strategy.setAssetManagement(b, from_=b)

    with must_revert(Error("Ownable: caller is not the owner")):
        aave_strategy.setTreasuryManager(b, from_=b)

    with must_revert(Error("Ownable: caller is not the owner")):
        aave_strategy.setStkAave(b, from_=b)

    with must_revert(Error("IPOR_505")):
        aave_strategy.setTreasury(b, from_=b)

    tx = aave_strategy.setAssetManagement(b, from_=a)
    assert IStrategy.AssetManagementChanged(b.address) in tx.events
    assert aave_strategy.getAssetManagement() == b.address

    tx = aave_strategy.setTreasuryManager(b, from_=a)
    assert IStrategy.TreasuryManagerChanged(b.address) in tx.events
    assert aave_strategy.getTreasuryManager() == b.address

    with must_revert(Error("IPOR_505")):
        aave_strategy.setTreasury(b, from_=a)

    tx = aave_strategy.setTreasury(b, from_=b)
    assert IStrategy.TreasuryChanged(b.address) in tx.events
    assert aave_strategy.getTreasury() == b.address

    tx = aave_strategy.setStkAave(b, from_=a)
    assert StrategyAave.StkAaveChanged(b.address) in tx.events


@pytest.mark.parametrize("setup_aave", ["setup_aave_dai_fixture", "setup_aave_usdc_fixture", "setup_aave_usdt_fixture"])
def test_aave_apr(setup_aave, request):
    aave_strategy, aasset, asset, aave_pool_provider, _, _, _ = request.getfixturevalue(setup_aave)
    assert isinstance(aave_strategy, StrategyAave)
    assert isinstance(aave_pool_provider, AaveLendingPoolProviderV2)

    pool = AaveLendingPoolV2(aave_pool_provider.getLendingPool())
    apr = pool.getReserveData(asset).currentLiquidityRate / 10 ** 27
    seconds_per_year = 365 * 24 * 60 * 60
    apy = (1 + apr / seconds_per_year) ** seconds_per_year - 1

    print(asset.name())
    print(f"{apy * 100}%")
    print(f"{aave_strategy.getApy() / 10 ** 18 * 100}%")
    print(f"relative error: {abs(apy - apr) / apy * 100}%")
    #print(f"{apr * 100}%") same as above


@pytest.mark.parametrize("setup_aave", ["setup_aave_dai_fixture", "setup_aave_usdc_fixture", "setup_aave_usdt_fixture"])
@on_revert(lambda e: print(e.tx.call_trace))
def test_compound_deposit_withdraw(setup_aave, request):
    aave_strategy, aasset, asset, aave_pool_provider, aave, stk_aave, incentives = request.getfixturevalue(setup_aave)
    assert isinstance(aave_strategy, StrategyAave)
    assert isinstance(aave_pool_provider, AaveLendingPoolProviderV2)
    assert isinstance(asset, IERC20Metadata)
    assert isinstance(aasset, IERC20Metadata)
    assert isinstance(aave, IERC20Metadata)
    assert isinstance(stk_aave, StakedAaveInterface)
    assert isinstance(incentives, AaveIncentivesInterface)

    a = default_chain.accounts[0]
    aave_strategy.setAssetManagement(a)
    assert aave_strategy.balanceOf() == 0

    deposited_amount = random_int(10_000, 100_000) * (10 ** asset.decimals())
    assert asset.balanceOf(a) >= deposited_amount
    assert aasset.balanceOf(aave_strategy) == 0

    # decimals of asset and aasset are the same
    assert asset.decimals() == aasset.decimals()

    asset.approve(aave_strategy, deposited_amount)
    # convert deposited_amount to wads
    tx = aave_strategy.deposit(deposited_amount * 10 ** (18 - asset.decimals()))
    # aave seems to mint deposited_amount +- 1
    assert abs(aasset.balanceOf(aave_strategy, block=tx.block_number) - deposited_amount) <= 1
    assert abs(aave_strategy.balanceOf(block=tx.block_number) - deposited_amount * 10 ** (18 - asset.decimals())) <= 10 ** (18 - asset.decimals())

    # burn remaining balance
    asset.transfer(Address(1), asset.balanceOf(a), from_=a)

    # withdraw half
    balance = aave_strategy.balanceOf() // (10 ** (18 - asset.decimals()))
    aave_strategy.withdraw(balance // 2 * 10 ** (18 - asset.decimals()))

    assert asset.balanceOf(a) == balance // 2
    assert aasset.balanceOf(aave_strategy) >= balance - balance // 2

    # withdraw the rest
    aave_strategy.withdraw(aave_strategy.balanceOf())
    assert asset.balanceOf(a) >= deposited_amount

    # claim rewards
    assert aave.balanceOf(aave_strategy) == 0
    assert aave.balanceOf(a) == 0
    aave_strategy.setTreasury(a)

    with may_revert(Error("INVALID_BALANCE_ON_COOLDOWN")):
        tx = aave_strategy.beforeClaim()
        assert StrategyAave.DoBeforeClaim(a.address, [aasset.address]) in tx.events

        default_chain.mine(lambda x: x + stk_aave.COOLDOWN_SECONDS() + 1)
        tx = aave_strategy.doClaim()
        assert IStrategy.DoClaim(a.address, aasset.address, a.address, aave.balanceOf(a)) in tx.events
