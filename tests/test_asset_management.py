import pytest

from wake.testing import *
from pytypes.source.contracts.interfaces.IStrategy import IStrategy
from pytypes.source.contracts.tokens.IvToken import IvToken
from pytypes.source.contracts.vault.AssetManagementDai import AssetManagementDai
from pytypes.source.contracts.vault.AssetManagementUsdc import AssetManagementUsdc
from pytypes.source.contracts.vault.AssetManagementUsdt import AssetManagementUsdt
from pytypes.source.contracts.vault.AssetManagement import AssetManagement
from pytypes.openzeppelin.contracts.token.ERC20.extensions.IERC20Metadata import IERC20Metadata
from .config import FORK_URL
from .test_aave import setup_aave_dai, setup_aave_usdc, setup_aave_usdt
from .test_compound import setup_compound_dai, setup_compound_usdc, setup_compound_usdt
from .utils import deploy_with_proxy


@pytest.fixture
def setup_asset_management_dai():
    with default_chain.connect(fork=FORK_URL):
        a = default_chain.accounts[0]
        default_chain.set_default_accounts(a)

        dai = IERC20Metadata("0x6B175474E89094C44Da98b954EedeAC495271d0F")
        assert dai.symbol() == "DAI"

        asset_management = deploy_with_proxy(AssetManagementDai)
        ivdai = IvToken.deploy("IvDAI", "IVDAI", dai)
        ivdai.setAssetManagement(asset_management)

        aave_strategy, *_ = setup_aave_dai()
        compound_strategy, *_ = setup_compound_dai()

        asset_management.initialize(dai, ivdai, aave_strategy, compound_strategy)
        yield asset_management, dai, ivdai, aave_strategy, compound_strategy


@pytest.fixture
def setup_asset_management_usdc():
    with default_chain.connect(fork=FORK_URL):
        a = default_chain.accounts[0]
        default_chain.set_default_accounts(a)

        usdc = IERC20Metadata("0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48")
        assert usdc.symbol() == "USDC"

        asset_management = deploy_with_proxy(AssetManagementUsdc)
        ivusdc = IvToken.deploy("IvUSDC", "IVUSDC", usdc)
        ivusdc.setAssetManagement(asset_management)

        aave_strategy, *_ = setup_aave_usdc()
        compound_strategy, *_ = setup_compound_usdc()

        asset_management.initialize(usdc, ivusdc, aave_strategy, compound_strategy)
        yield asset_management, usdc, ivusdc, aave_strategy, compound_strategy


@pytest.fixture
def setup_asset_management_usdt():
    with default_chain.connect(fork=FORK_URL):
        a = default_chain.accounts[0]
        default_chain.set_default_accounts(a)

        usdt = IERC20Metadata("0xdac17f958d2ee523a2206206994597c13d831ec7")
        assert usdt.symbol() == "USDT"

        asset_management = deploy_with_proxy(AssetManagementUsdt)
        ivusdt = IvToken.deploy("IvUSDT", "IVUSDT", usdt)
        ivusdt.setAssetManagement(asset_management)

        aave_strategy, *_ = setup_aave_usdt()
        compound_strategy, *_ = setup_compound_usdt()

        asset_management.initialize(usdt, ivusdt, aave_strategy, compound_strategy)
        yield asset_management, usdt, ivusdt, aave_strategy, compound_strategy


@pytest.mark.parametrize("setup_asset_management", ["setup_asset_management_dai", "setup_asset_management_usdc", "setup_asset_management_usdt"])
def test_asset_management_core(setup_asset_management, request):
    asset_management, asset, ivasset, aave_strategy, compound_strategy = request.getfixturevalue(setup_asset_management)
    assert isinstance(asset_management, AssetManagement)
    assert isinstance(asset, IERC20Metadata)
    assert isinstance(ivasset, IvToken)
    assert isinstance(aave_strategy, IStrategy)
    assert isinstance(compound_strategy, IStrategy)

    a = default_chain.accounts[0]

    assert asset_management.getAsset() == asset.address
    assert asset_management.getIvToken() == ivasset.address
    assert asset_management,getAmmTreasury() == Address.ZERO
    assert asset_management.getStrategyAave() == aave_strategy.address
    assert asset_management.getStrategyCompound() == compound_strategy.address

    tx = asset_management.setAmmTreasury(a)
    assert AssetManagement.AmmTreasuryChanged(a.address) in tx.events

    if asset.symbol() == "DAI":
        new_aave_strategy = setup_aave_dai()[0]
    elif asset.symbol() == "USDC":
        new_aave_strategy = setup_aave_usdc()[0]
    elif asset.symbol() == "USDT":
        new_aave_strategy = setup_aave_usdt()[0]
    else:
        raise Exception("Unknown asset")

    tx = asset_management.setStrategyAave(new_aave_strategy)
    assert AssetManagement.StrategyChanged(new_aave_strategy.address, new_aave_strategy.getShareToken()) in tx.events

    if asset.symbol() == "DAI":
        new_compound_strategy = setup_compound_dai()[0]
    elif asset.symbol() == "USDC":
        new_compound_strategy = setup_compound_usdc()[0]
    elif asset.symbol() == "USDT":
        new_compound_strategy = setup_compound_usdt()[0]
    else:
        raise Exception("Unknown asset")

    tx = asset_management.setStrategyCompound(new_compound_strategy)
    assert AssetManagement.StrategyChanged(new_compound_strategy.address, new_compound_strategy.getShareToken()) in tx.events
