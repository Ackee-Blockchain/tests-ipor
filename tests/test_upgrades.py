from typing import Tuple, Type
import pytest

from woke.testing import *
from pytypes.source.contracts.amm.AmmStorage import AmmStorage
from pytypes.source.contracts.amm.libraries.SoapIndicatorRebalanceLogic import SoapIndicatorRebalanceLogic
from pytypes.source.contracts.interfaces.types.AmmStorageTypes import AmmStorageTypes
from pytypes.source.contracts.interfaces.types.AmmTypes import AmmTypes
from pytypes.source.contracts.interfaces.types.IporTypes import IporTypes

from pytypes.v1.contracts.interfaces.IStanleyInternal import IStanleyInternal
from pytypes.v1.contracts.interfaces.types.MiltonStorageTypes import MiltonStorageTypes
from pytypes.source.contracts.vault.AssetManagement import AssetManagement
from pytypes.source.contracts.vault.AssetManagementDai import AssetManagementDai
from pytypes.source.contracts.vault.AssetManagementUsdc import AssetManagementUsdc
from pytypes.source.contracts.vault.AssetManagementUsdt import AssetManagementUsdt

from pytypes.v1.contracts.interfaces.IStrategyAave import IStrategyAave as IStrategyAaveV1
from pytypes.source.contracts.vault.strategies.StrategyAave import StrategyAave

from pytypes.v1.contracts.interfaces.IStrategyCompound import IStrategyCompound as IStrategyCompoundV1
from pytypes.source.contracts.vault.strategies.StrategyCompound import StrategyCompound

from pytypes.v1.contracts.interfaces.IIporOracle import IIporOracle as IIporOracleV1
from pytypes.source.contracts.oracles.IporOracle import IporOracle

from pytypes.v1.contracts.interfaces.IMiltonStorage import IMiltonStorage
from pytypes.v1.contracts.interfaces.types.IporTypes import IporTypes as IporTypesV1

from pytypes.openzeppelin.contractsupgradeable.proxy.utils.UUPSUpgradeable import UUPSUpgradeable
from pytypes.openzeppelin.contractsupgradeable.access.OwnableUpgradeable import OwnableUpgradeable

from .config import FORK_URL
from .setup import get_dai, get_usdc, get_usdt


def on_revert_handler(error: TransactionRevertedError):
    if error.tx is not None:
        print(error.tx.call_trace)
        print(error.tx.console_logs)


@pytest.mark.parametrize("params", [
    (Address("0xA6aC8B6AF789319A1Db994E25760Eb86F796e2B0"), AssetManagementDai),
    (Address("0x7aa7b0B738C2570C2f9F892cB7cA5bB89b9BF260"), AssetManagementUsdc),
    (Address("0x8e679C1d67Af0CD4b314896856f09ece9E64D6B5"), AssetManagementUsdt),
])
@default_chain.connect(fork=FORK_URL)
@on_revert(on_revert_handler)
def test_asset_mgmt_upgrade(params: Tuple[Address, Type[AssetManagement]]):
    a = default_chain.accounts[0]

    proxy = params[0]
    stanley_internal = IStanleyInternal(proxy)
    asset = stanley_internal.getAsset()
    milton = stanley_internal.getMilton()
    #iv_token = stanley_internal.getIvToken()
    strategy_aave = stanley_internal.getStrategyAave()
    strategy_compound = stanley_internal.getStrategyCompound()

    impl = params[1].deploy(from_=a)
    UUPSUpgradeable(proxy).upgradeTo(impl, from_=OwnableUpgradeable(proxy).owner())

    asset_mgmt = AssetManagement(proxy)
    assert asset_mgmt.getAsset() == asset
    assert asset_mgmt.getAmmTreasury() == milton
    assert asset_mgmt.getIvToken() != Address.ZERO
    #assert asset_mgmt.getIvToken() == iv_token
    assert asset_mgmt.getStrategyAave() == strategy_aave
    assert asset_mgmt.getStrategyCompound() == strategy_compound


@pytest.mark.parametrize("aave_strategy", [
    Address("0x526d0047725D48BBc6e24C7B82A3e47C1AF1f62f"),  # DAI
    Address("0x77fCaE921e3df22810c5a1aC1D33f2586BbA028f"),  # USDC
    Address("0x58703DA5295794ed4E82323fcce7371272c5127D"),  # USDT
])
@default_chain.connect(fork=FORK_URL)
@on_revert(on_revert_handler)
def test_aave_strategy_upgrade(aave_strategy: Address):
    a = default_chain.accounts[0]

    old = IStrategyAaveV1(aave_strategy)
    asset = old.getAsset()
    share_token = old.getShareToken()
    #apr = old.getApr()
    balance_of = old.balanceOf()
    stanley = old.getStanley()
    treasury = old.getTreasury()
    treasury_manager = old.getTreasuryManager()

    impl = StrategyAave.deploy(from_=a)
    UUPSUpgradeable(aave_strategy).upgradeTo(impl, from_=OwnableUpgradeable(aave_strategy).owner())

    new = StrategyAave(aave_strategy)
    assert new.getAsset() == asset
    assert new.getShareToken() == share_token
    #assert new.getApy() == apr
    assert new.balanceOf() == balance_of
    assert new.getAssetManagement() == stanley
    assert new.getTreasury() == treasury
    assert new.getTreasuryManager() == treasury_manager


@pytest.mark.parametrize("compound_strategy", [
    Address("0x87CEF19aCa214d12082E201e6130432Df39fc774"),  # DAI
    Address("0xe5257cf3Bd0eFD397227981fe7bbd55c7582f526"),  # USDC
    Address("0xE4cD9AA68Be5b5276573E24FA7A0007da29aB5B1"),  # USDT
])
@default_chain.connect(fork=FORK_URL)
@on_revert(on_revert_handler)
def test_compound_strategy_upgrade(compound_strategy: Address):
    a = default_chain.accounts[0]

    old = IStrategyCompoundV1(compound_strategy)
    asset = old.getAsset()
    share_token = old.getShareToken()
    #apr = old.getApr()
    balance_of = old.balanceOf()
    stanley = old.getStanley()
    treasury = old.getTreasury()
    treasury_manager = old.getTreasuryManager()

    impl = StrategyCompound.deploy(from_=a)
    UUPSUpgradeable(compound_strategy).upgradeTo(impl, from_=OwnableUpgradeable(compound_strategy).owner())

    new = StrategyCompound(compound_strategy)
    assert new.getAsset() == asset
    assert new.getShareToken() == share_token
    #assert new.getApy() == apr
    assert new.balanceOf() == balance_of
    assert new.getAssetManagement() == stanley
    assert new.getTreasury() == treasury
    assert new.getTreasuryManager() == treasury_manager


@pytest.mark.parametrize("asset", [
    Address("0x6B175474E89094C44Da98b954EedeAC495271d0F"),
    Address("0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"),
    Address("0xdac17f958d2ee523a2206206994597c13d831ec7"),
])
@default_chain.connect(fork=FORK_URL)
@on_revert(on_revert_handler)
def test_ipor_oracle_upgrade(asset: Address):
    a = default_chain.accounts[0]
    oracle = Address("0x421C69EAa54646294Db30026aeE80D01988a6876")
    timestamp = default_chain.blocks["latest"].timestamp

    old = IIporOracleV1(oracle)
    index = old.getIndex(asset)
    accrued_index = old.getAccruedIndex(timestamp, asset)
    accrued_ibt_price = old.calculateAccruedIbtPrice(asset, timestamp)
    assert old.isUpdater(Address("0xc3a53976e9855d815a08f577c2beef2a799470b7"))
    assert old.isAssetSupported(asset)

    impl = IporOracle.deploy(
        get_usdt(), 10 ** 18,
        get_dai(), 10 ** 18,
        get_usdc(), 10 ** 18,
        from_=a)
    owner = OwnableUpgradeable(oracle).owner()
    UUPSUpgradeable(oracle).upgradeTo(impl, from_=owner)

    new = IporOracle(oracle)
    new.postUpgrade([asset], from_=owner)
    #assert new.getIndex(asset) == index
    #assert new.getAccruedIndex(timestamp, asset) == accrued_index
    #assert new.calculateAccruedIbtPrice(asset, timestamp) == accrued_ibt_price
    assert new.isUpdater(Address("0xc3a53976e9855d815a08f577c2beef2a799470b7"))
    assert new.isAssetSupported(asset)


@pytest.mark.parametrize("params", [
    (Address("0xb99f2a02c0851efdD417bd6935d2eFcd23c56e61"), 100, 103),  # DAI
    (Address("0xB3d1c1aB4D30800162da40eb18B3024154924ba5"), 99, 101),  # USDC
    (Address("0x364f116352EB95033D73822bA81257B8c1f5B1CE"), 100, 101),  # USDT
])
@default_chain.connect(fork=FORK_URL)
@on_revert(on_revert_handler)
def test_amm_storage_upgrade(params: Tuple[Address, int, int]):
    def compare_swap(swap1: IporTypesV1.IporSwapMemory, swap2: AmmTypes.Swap) -> bool:
        if swap2.tenor == IporTypes.SwapTenor.DAYS_28:
            tenor_seconds = 28 * 24 * 60 * 60
        elif swap2.tenor == IporTypes.SwapTenor.DAYS_60:
            tenor_seconds = 60 * 24 * 60 * 60
        elif swap2.tenor == IporTypes.SwapTenor.DAYS_90:
            tenor_seconds = 90 * 24 * 60 * 60
        else:
            raise ValueError("Unknown tenor")

        return (
            swap1.id == swap2.id and
            swap1.buyer == swap2.buyer and
            swap1.openTimestamp == swap2.openTimestamp and
            swap1.endTimestamp == swap2.openTimestamp + tenor_seconds and
            swap1.idsIndex == swap2.idsIndex and
            swap1.collateral == swap2.collateral and
            swap1.notional == swap2.notional and
            swap1.ibtQuantity == swap2.ibtQuantity and
            swap1.fixedInterestRate == swap2.fixedInterestRate and
            swap1.liquidationDepositAmount == swap2.liquidationDepositAmount and
            swap1.state == swap2.state
        )

    def compare_swap_ids(swap_id1: MiltonStorageTypes.IporSwapId, swap_id2: AmmStorageTypes.IporSwapId) -> bool:
        return (
            swap_id1.id == swap_id2.id and
            swap_id1.direction == swap_id2.direction
        )

    a = default_chain.accounts[0]
    proxy, pay_fixed_id, receive_fixed_id = params

    old = IMiltonStorage(proxy)
    swap_opener = Address("0xFd9f45f118F0A6aaa0EB1491576e79E6899C4e35")

    SoapIndicatorRebalanceLogic.deploy(from_=a)

    with default_chain.snapshot_and_revert():
        default_chain.mine()  # simulate deploy
        default_chain.mine()  # simulate upgradeTo
        block_number = default_chain.blocks["latest"].number

        milton = old.getMilton()
        joseph = old.getJoseph()
        last_swap_id = old.getLastSwapId()
        balance = old.getBalance()
        extended_balance = old.getExtendedBalance()
        total_outstanding_notional = old.getTotalOutstandingNotional()
        swap_pay_fixed = old.getSwapPayFixed(pay_fixed_id)
        swap_receive_fixed = old.getSwapReceiveFixed(receive_fixed_id)
        swaps_pay_fixed = old.getSwapsPayFixed(swap_opener, 0, 50)
        swaps_receive_fixed = old.getSwapsReceiveFixed(swap_opener, 0, 50)
        swap_pay_fixed_ids = old.getSwapPayFixedIds(swap_opener, 0, 50)
        swap_receive_fixed_ids = old.getSwapReceiveFixedIds(swap_opener, 0, 50)
        swap_ids = old.getSwapIds(swap_opener, 0, 50)
        soap = old.calculateSoap(10 ** 18, default_chain.blocks["latest"].timestamp)
        soap_pay_fixed = old.calculateSoapPayFixed(10 ** 18, default_chain.blocks["latest"].timestamp)
        soap_receive_fixed = old.calculateSoapReceiveFixed(10 ** 18, default_chain.blocks["latest"].timestamp)

    impl = AmmStorage.deploy(Address(1), Address(1), from_=a)
    owner = OwnableUpgradeable(proxy).owner()
    UUPSUpgradeable(proxy).upgradeTo(impl, from_=owner)

    assert default_chain.blocks["latest"].number == block_number

    new = AmmStorage(proxy)
    new.postUpgrade(from_=owner)
    assert new.getLastSwapId() == last_swap_id
    assert new.getBalance() == IporTypes.AmmBalancesMemory(
        balance.totalCollateralPayFixed,
        balance.totalCollateralReceiveFixed,
        balance.liquidityPool,
        balance.vault,
    )
    assert new.getExtendedBalance() == AmmStorageTypes.ExtendedBalancesMemory(
        extended_balance.totalCollateralPayFixed,
        extended_balance.totalCollateralReceiveFixed,
        extended_balance.liquidityPool,
        extended_balance.vault,
        extended_balance.iporPublicationFee,
        extended_balance.treasury,
    )
    assert new.getBalancesForOpenSwap().totalNotionalPayFixed == total_outstanding_notional[0]
    assert new.getBalancesForOpenSwap().totalNotionalReceiveFixed == total_outstanding_notional[1]
    assert compare_swap(
        swap_pay_fixed,
        new.getSwap(AmmTypes.SwapDirection.PAY_FIXED_RECEIVE_FLOATING, pay_fixed_id),
    )
    assert compare_swap(
        swap_receive_fixed,
        new.getSwap(AmmTypes.SwapDirection.PAY_FLOATING_RECEIVE_FIXED, receive_fixed_id),
    )
    swaps_pay_fixed2 = new.getSwapsPayFixed(swap_opener, 0, 50)
    assert swaps_pay_fixed[0] == swaps_pay_fixed2[0]
    assert all(compare_swap(s1, s2) for s1, s2 in zip(swaps_pay_fixed[1], swaps_pay_fixed2[1]))
    swaps_receive_fixed2 = new.getSwapsReceiveFixed(swap_opener, 0, 50)
    assert swaps_receive_fixed[0] == swaps_receive_fixed2[0]
    assert all(compare_swap(s1, s2) for s1, s2 in zip(swaps_receive_fixed[1], swaps_receive_fixed2[1]))
    swap_ids2 = new.getSwapIds(swap_opener, 0, 50)
    assert swap_ids[0] == swap_ids2[0]
    assert all(compare_swap_ids(s1, s2) for s1, s2 in zip(swap_ids[1], swap_ids2[1]))


# Milton -> AmmTreasury will be upgraded but the new version of contract does not use storage at all
