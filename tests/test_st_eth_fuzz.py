from bisect import bisect_right
from dataclasses import dataclass
import dataclasses
import logging
import math
import random
from typing import Callable, Dict

from wake.testing import *
from wake.testing.fuzzing import *
from pytypes.source.contracts.ammeth.AmmPoolsLensStEth import AmmPoolsLensStEth
from pytypes.source.contracts.ammeth.interfaces.IAmmPoolsServiceStEth import IAmmPoolsServiceStEth
from pytypes.source.contracts.ammeth.interfaces.IStETH import IStETH
from pytypes.source.contracts.ammeth.interfaces.IwstEth import IwstEth
from pytypes.source.contracts.base.amm.libraries.SwapEventsBaseV1 import SwapEventsBaseV1
from pytypes.source.contracts.base.events.AmmEventsBaseV1 import AmmEventsBaseV1
from pytypes.source.contracts.base.interfaces.IAmmStorageBaseV1 import IAmmStorageBaseV1
from pytypes.source.contracts.interfaces.IAmmCloseSwapLens import IAmmCloseSwapLens
from pytypes.source.contracts.interfaces.IAmmCloseSwapServiceStEth import IAmmCloseSwapServiceStEth
from pytypes.source.contracts.interfaces.IAmmGovernanceService import IAmmGovernanceService
from pytypes.source.contracts.interfaces.IAmmOpenSwapServiceStEth import IAmmOpenSwapServiceStEth
from pytypes.source.contracts.interfaces.IAmmSwapsLens import IAmmSwapsLens
from pytypes.source.contracts.interfaces.types.AmmTypes import AmmTypes
from pytypes.source.contracts.interfaces.types.IporTypes import IporTypes
from pytypes.source.contracts.oracles.IporOracle import IporOracle

from pytypes.source.contracts.router.IporProtocolRouter import IporProtocolRouter
from pytypes.openzeppelin.contracts.token.ERC20.extensions.IERC20Metadata import IERC20Metadata

from .config import FORK_URL
from .setup import setup_router, get_oracle, get_steth, get_weth, get_wsteth
from .utils import mint


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

names = [
    "Alice",
    "Bob",
    "Charlie",
    "Dave",
    "Eve",
    "Faythe",
    "Grace",
    "Heidi",
    "Ivan",
    "Judy",
]


@dataclass
class Swap:
    buyer: Account
    collateral: uint256  # in 18 decimals
    notional: uint256  # in 18 decimals
    leverage: uint256  # in 18 decimals
    fixed_rate: uint256  # in 18 decimals
    ibt_quantity: uint256  # amount of IBT tokens (notional / ibtPrice at the time of swap creation), in 18 decimals
    pay_fixed: bool
    open_timestamp: uint256
    tenor: IporTypes.SwapTenor


def div(a, b):
    return (a + b // 2) // b


def div_int(a, b):
    q, r = divmod(a, b)
    return q + (2 * r // b)


class StETHFuzzTest(FuzzTest):
    _liquidation_deposit: uint256  # in 18 decimals
    _publication_fee: uint256  # in 18 decimals
    _opening_fee_rate: uint256  # in 18 decimals
    _min_leverage: uint256  # in 18 decimals
    _time_before_maturity_community: uint256  # in seconds
    _time_before_maturity_buyer: uint256  # in seconds
    _min_liquidation_threshold_community: uint256  # in 18 decimals
    _min_liquidation_threshold_buyer: uint256  # in 18 decimals
    _unwinding_fee_rate: uint256  # in 18 decimals
    _redeem_fee_rate: uint256  # in 18 decimals
    _max_collateral_ratio: uint256  # max value of (open swap collateral / liquidity pool collateral) * 10 ** 4 for both types
    _max_collateral_ratio_pay_fixed: uint256  # max value of (open swap collateral / liquidity pool collateral) * 10 ** 4 for open swap pay fixed
    _max_collateral_ratio_receive_fixed: uint256  # max value of (open swap collateral / liquidity pool collateral) * 10 ** 4 for open swap receive fixed
    _max_leverage_pay_fixed: uint256  # max value of (max_notional_per_leg / max_collateral_per_leg) in wads
    _max_leverage_receive_fixed: uint256  # max value of (max_notional_per_leg / max_collateral_per_leg) in wads
    _opening_fee_treasury_portion_rate: uint256  # in 18 decimals
    _unwinding_fee_treasury_portion_rate: uint256  # in 18 decimals
    _time_after_open_wihout_unwinding: uint256  # in seconds

    _message_signer: Account
    _router: IporProtocolRouter
    _oracle: IporOracle
    _steth: IERC20Metadata
    _weth: IERC20Metadata
    _wsteth: IERC20Metadata
    _ipst_eth: IERC20Metadata

    _steth_treasury: Account
    _steth_storage: IAmmStorageBaseV1

    _treasuries: Dict[IERC20Metadata, Account]
    _balances: Dict[IERC20Metadata, Dict[Account, uint256]]
    _eth_balances: Dict[Account, uint256]
    _ipor_treasury: uint256  # amount of stETH in stETH treasury belonging to IPOR
    _swaps: Dict[uint32, Swap]
    _closed_swaps: Dict[uint32, Swap]
    _open_swap_functions: Dict[IporTypes.SwapTenor, Dict[bool, Callable]]

    _quasiIbtPrice: uint256
    _risk_indicators: Dict[IporTypes.SwapTenor, Dict[bool, AmmTypes.RiskIndicatorsInputs]]

    _max_ip_error: uint256  # in ipstETH
    _max_redeem_error: uint256  # in stETH
    _max_payoff_error: uint256  # in stETH
    _max_pnl_error: uint256  # in stETH
    _max_ip_exchange_rate_error: float  # relative error
    _max_ibt_quantity_error: uint256  # in IBT "tokens"

    def pre_sequence(self) -> None:
        self._max_ip_error = 0
        self._max_redeem_error = 0
        self._max_payoff_error = 0
        self._max_pnl_error = 0
        self._max_soap_error = 0
        self._max_ip_exchange_rate_error = 0
        self._max_ibt_quantity_error = 0

        self._liquidation_deposit = random_int(1, 30) * 10 ** 16
        self._publication_fee = random_int(1, 10) * 10 ** 16
        self._opening_fee_rate = random_int(1, 20) * 10 ** 15  # 0.1% - 2%
        self._min_leverage = 10 * 10 ** 18  # 10x
        self._time_before_maturity_community = 1 * 60 * 60  # 1 hour
        self._time_before_maturity_buyer = 24 * 60 * 60  # 24 hours
        self._min_liquidation_threshold_community = 995 * 10 ** 15  # 99.5%
        self._min_liquidation_threshold_buyer = 990 * 10 ** 15  # 99%
        self._unwinding_fee_rate = random_int(1, 20) * 10 ** 15  # 0.1% - 2%
        self._redeem_fee_rate = random_int(1, 10) * 10 ** 15  # 0.1% - 1%
        self._max_collateral_ratio = 10 ** 17
        self._max_collateral_ratio_pay_fixed = 10 ** 17
        self._max_collateral_ratio_receive_fixed = 10 ** 17
        self._max_leverage_pay_fixed = 20 * 10 ** 18  # 20x
        self._max_leverage_receive_fixed = 20 * 10 ** 18  # 20x
        self._opening_fee_treasury_portion_rate = random_int(1, 20) * 10 ** 15  # 0.1% - 2%
        self._unwinding_fee_treasury_portion_rate = random_int(1, 20) * 10 ** 15  # 0.1% - 2%
        self._time_after_open_wihout_unwinding = random_int(2, 10) * 24 * 60 * 60  # 2-10 days

        self._message_signer = Account.new()
        self._router = setup_router(
            self._message_signer,
            liquidation_deposit=self._liquidation_deposit // 10 ** 12,
            publication_fee=self._publication_fee,
            opening_fee_rate=self._opening_fee_rate,
            min_leverage=self._min_leverage,
            redeem_fee_rate=self._redeem_fee_rate,
            time_before_maturiy_buyer=self._time_before_maturity_buyer,
            time_before_maturity_community=self._time_before_maturity_community,
            min_liquidation_threshold_buyer=self._min_liquidation_threshold_buyer,
            min_liquidation_threshold_community=self._min_liquidation_threshold_community,
            unwinding_fee_rate=self._unwinding_fee_rate,
            opening_fee_treasury_portion_rate=self._opening_fee_treasury_portion_rate,
            unwinding_fee_treasury_portion_rate=self._unwinding_fee_treasury_portion_rate,
            time_after_open_wihout_unwinding=self._time_after_open_wihout_unwinding,
        )
        logger.info("Contracts deployed")
        self._oracle = get_oracle()
        self._oracle.addUpdater(default_chain.accounts[0])

        pools_lens = AmmPoolsLensStEth(self._router.getConfiguration().ammPoolsLensStEth)

        self._steth = get_steth()
        assert self._steth.decimals() == 18
        self._weth = get_weth()
        assert self._weth.decimals() == 18
        self._wsteth = get_wsteth()
        assert self._wsteth.decimals() == 18
        self._ipst_eth = IERC20Metadata(pools_lens.ipstEth())
        self._steth_treasury = Account(pools_lens.ammTreasuryStEth())
        self._steth_storage = IAmmStorageBaseV1(pools_lens.ammStorageStEth())
        self._balances = {
            self._steth: {},
            self._weth: {},
            self._wsteth: {},
            self._ipst_eth: {},
        }
        self._eth_balances = {}
        self._swaps = {}
        self._closed_swaps = {}
        self._ipor_treasury = 0

        for acc in default_chain.accounts:
            self._eth_balances[acc] = acc.balance

        for acc in default_chain.accounts:
            assert self._ipst_eth.balanceOf(acc) == 0
            self._balances[self._ipst_eth][acc] = 0

        assert self._steth.balanceOf(self._steth_treasury) == 0
        self._balances[self._steth][self._steth_treasury] = 0

        # set stETH pool params
        IAmmGovernanceService(self._router).setAmmPoolsParams(
            self._steth,
            100_000_000,  # max amount of liquidity pool balance
            1,  # rebalancing is not performed with stETH
            1,  # rebalancing is not performed with stETH
        )

        a = default_chain.accounts[0]
        for asset in [self._steth, self._weth, self._wsteth]:
            for acc in default_chain.accounts:
                self._balances[asset][acc] = asset.balanceOf(acc)

            if asset != self._wsteth:
                self._provide_liquidity(asset, 10_000 * 10 ** 18, a, a)

        self._provide_liquidity_eth(10_000, a, a)

        self._open_swap_functions = {
            IporTypes.SwapTenor.DAYS_28: {
                True: IAmmOpenSwapServiceStEth(self._router).openSwapPayFixed28daysStEth,
                False: IAmmOpenSwapServiceStEth(self._router).openSwapReceiveFixed28daysStEth,
            },
            IporTypes.SwapTenor.DAYS_60: {
                True: IAmmOpenSwapServiceStEth(self._router).openSwapPayFixed60daysStEth,
                False: IAmmOpenSwapServiceStEth(self._router).openSwapReceiveFixed60daysStEth,
            },
            IporTypes.SwapTenor.DAYS_90: {
                True: IAmmOpenSwapServiceStEth(self._router).openSwapPayFixed90daysStEth,
                False: IAmmOpenSwapServiceStEth(self._router).openSwapReceiveFixed90daysStEth,
            },
        }

        self._risk_indicators = {
            IporTypes.SwapTenor.DAYS_28: {},
            IporTypes.SwapTenor.DAYS_60: {},
            IporTypes.SwapTenor.DAYS_90: {},
        }

        t = default_chain.blocks["latest"].timestamp
        self._quasiIbtPrice = 0
        self._ipor_indexes = [0]
        self._times = [t]
        self._oracle.addAsset(self._steth, t)

        default_chain.mine(lambda x: x + random_int(1, 10_000))

        # start with anything between 0.1% and 10%
        self._update_ipor_index(random_int(10**15, 10**17))

    def pre_invariants(self) -> None:
        latest_timestamp = default_chain.blocks["latest"].timestamp

        # close all swaps that expired
        swaps_to_close = []
        for swap_id, swap in self._swaps.items():
            if swap.open_timestamp + self._get_tenor_length(swap.tenor) * 24 * 60 * 60 < latest_timestamp:
                # swap has expired, close it
                swaps_to_close.append(swap_id)

        for swap_id in swaps_to_close:
            self._close_swap(swap_id)

    def post_invariants(self) -> None:
        # roll forward time
        time_change = random_int(1 * 24 * 60 * 60, 20 * 24 * 60 * 60)  # 1-20 days
        default_chain.mine(lambda x: x + time_change)

    def _update_ipor_index(self, new_index: uint256):
        t = default_chain.blocks["latest"].timestamp
        self._quasiIbtPrice += self._ipor_indexes[-1] * (t - self._times[-1])
        self._ipor_indexes.append(new_index)
        self._times.append(t)

        self._oracle.updateIndexes(
            [
                IporOracle.UpdateIndexParams(
                    self._steth.address,
                    new_index,
                    t,
                    self._quasiIbtPrice,
                ),
            ]
        )

    def _get_ibt_price(self, timestamp: uint256) -> uint256:
        quasi = self._quasiIbtPrice + self._ipor_indexes[-1] * (timestamp - self._times[-1])
        return round(math.exp(quasi / (365 * 24 * 60 * 60 * 10 ** 18)) * 10 ** 18)

    def pre_flow(self, flow: Callable) -> None:
        # update IPOR indexes
        add = random_bool()
        difference = random_int(5 * 10 ** 14, 25 * 10 ** 14)  # 0.05% - 2.25%

        # must be positive
        if not add and self._ipor_indexes[-1] <= difference:
            add = True

        # must be less than 10%
        if add and self._ipor_indexes[-1] + difference > 10 ** 17:
            add = False

        if not add:
            difference = -difference
        ipor_index = self._ipor_indexes[-1] + difference
        self._update_ipor_index(ipor_index)

        p = min(20, len(self._ipor_indexes))

        receive_fixed_spread = -random_int(1 * 10 ** 15, 5 * 10 ** 15)  # 0.1% - 0.5%
        pay_fixed_spread = (sum(self._ipor_indexes[-p:]) // p - ipor_index) // 10 ** 12
        if pay_fixed_spread < 0:
            pay_fixed_spread += random_int(1 * 10 ** 15, 3 * 10 ** 15)
        min_pay_fixed_rate = 1 * 10 ** 15  # 0.1%
        max_receive_fixed_rate = 1 * 10 ** 17  # 10%

        pay_fixed_indicators = AmmTypes.RiskIndicatorsInputs(
            self._max_collateral_ratio,
            self._max_collateral_ratio_pay_fixed,
            self._max_leverage_pay_fixed,
            pay_fixed_spread,
            min_pay_fixed_rate,
            20,
            default_chain.blocks["pending"].timestamp + random_int(1 * 24 * 60 * 60, 20 * 24 * 60 * 60),
            bytearray(),
        )
        receive_fixed_indicators = AmmTypes.RiskIndicatorsInputs(
            self._max_collateral_ratio,
            self._max_collateral_ratio_receive_fixed,
            self._max_leverage_receive_fixed,
            receive_fixed_spread,
            max_receive_fixed_rate,
            20,
            default_chain.blocks["pending"].timestamp + random_int(1 * 24 * 60 * 60, 20 * 24 * 60 * 60),
            bytearray(),
        )

        for tenor in IporTypes.SwapTenor:
            self._risk_indicators[tenor][True] = self._sign_risk_indicators(pay_fixed_indicators, tenor, 0)
            self._risk_indicators[tenor][False] = self._sign_risk_indicators(receive_fixed_indicators, tenor, 1)

    def _sign_risk_indicators(self, i: AmmTypes.RiskIndicatorsInputs, tenor: IporTypes.SwapTenor, direction: uint256):
        h = keccak256(Abi.encode_packed(
            ["uint256", "uint256", "uint256", "int256", "uint256", "uint256", "uint256", "address", "uint256", "uint256"],
            [
                i.maxCollateralRatio, i.maxCollateralRatioPerLeg, i.maxLeveragePerLeg, i.baseSpreadPerLeg, i.fixedRateCapPerLeg,
                i.demandSpreadFactor, i.expiration, self._steth, tenor, direction,
            ],
        ))
        return dataclasses.replace(i, signature=bytearray(self._message_signer.sign_hash(h)))

    def _calculate_pnl_raw(self, swap: Swap, block: int):
        payoff_timestamp = default_chain.blocks[block].timestamp
        delta_time = payoff_timestamp - swap.open_timestamp

        interest_fixed = swap.notional / 10 ** 18 * math.exp(swap.fixed_rate / 10 ** 18 * delta_time / (365 * 24 * 60 * 60))
        interest_fixed_wad = round(interest_fixed * 10 ** 18)

        start_index = bisect_right(self._times, swap.open_timestamp) - 1
        assert self._times[start_index] <= swap.open_timestamp
        assert len(self._times) == start_index + 1 or self._times[start_index + 1] > swap.open_timestamp

        end_index = bisect_right(self._times, payoff_timestamp) - 1
        assert self._times[end_index] <= payoff_timestamp
        assert len(self._times) == end_index + 1 or self._times[end_index + 1] > payoff_timestamp

        if start_index == end_index:
            interest_floating = swap.notional / 10 ** 18 * math.exp(self._ipor_indexes[start_index] / 10 ** 18 * delta_time / (365 * 24 * 60 * 60))
        else:
            interest_floating = swap.notional / 10 ** 18 * math.exp(self._ipor_indexes[start_index] / 10 ** 18 * (self._times[start_index + 1] - swap.open_timestamp) / (365 * 24 * 60 * 60))
            for i in range(start_index + 1, end_index):
                interest_floating *= math.exp(self._ipor_indexes[i] / 10 ** 18 * (self._times[i + 1] - self._times[i]) / (365 * 24 * 60 * 60))
            interest_floating *= math.exp(self._ipor_indexes[end_index] / 10 ** 18 * (payoff_timestamp - self._times[end_index]) / (365 * 24 * 60 * 60))

        interest_floating_wad = round(interest_floating * 10 ** 18)

        if swap.pay_fixed:
            pnl = interest_floating_wad - interest_fixed_wad
        else:
            pnl = interest_fixed_wad - interest_floating_wad

        if pnl > 0:
            if pnl > swap.collateral:
                pnl = swap.collateral
        else:
            if pnl < -swap.collateral:
                pnl = -swap.collateral
        return pnl

    # IMPORTANT: must be called in the context of the latest block - we do not keep history of all swaps
    def _calculate_soap(self):
        expected_soap_pay_fixed = 0
        expected_soap_receive_fixed = 0
        latest_block = default_chain.blocks["latest"].number

        for swap in self._swaps.values():
            if swap.pay_fixed:
                expected_soap_pay_fixed += self._calculate_pnl_raw(swap, latest_block)
            else:
                expected_soap_receive_fixed += self._calculate_pnl_raw(swap, latest_block)

        return expected_soap_pay_fixed, expected_soap_receive_fixed

    # IMPORTANT: must be called in the context of the latest block - we do not keep history of all swaps
    def _calculate_ip_exchange_rate(self):
        total_supply = self._ipst_eth.totalSupply()

        if total_supply == 0:
            return 10 ** 18
        else:
            lp_balance = (
                self._steth.balanceOf(self._steth_treasury)
                - sum(s.collateral for s in self._swaps.values())
                - len(self._swaps) * (self._liquidation_deposit + self._publication_fee)
                - len(self._closed_swaps) * self._publication_fee
                - self._ipor_treasury
            )
            return div((lp_balance - sum(self._calculate_soap())) * 10 ** 18, total_supply)

    def _get_tenor_length(self, tenor: IporTypes.SwapTenor) -> int:
        if tenor == IporTypes.SwapTenor.DAYS_28:
            return 28
        elif tenor == IporTypes.SwapTenor.DAYS_60:
            return 60
        elif tenor == IporTypes.SwapTenor.DAYS_90:
            return 90
        else:
            raise ValueError("Invalid tenor")

    @flow()
    def flow_provide_liquidity(self):
        provider = random_account()
        beneficiary = random_account(predicate=lambda a: a != default_chain.accounts[0])
        asset = random.choice([self._steth, self._weth, IERC20Metadata(Address.ZERO)])
        eth_amount = random_int(1, 100)

        if asset.address == Address(0):
            self._provide_liquidity_eth(eth_amount * 10 ** 18, provider, beneficiary)
        else:
            amount = eth_amount * 10 ** asset.decimals()

            self._provide_liquidity(asset, amount, provider, beneficiary)

    def _steth_shares_to_balance(self, shares: uint256) -> uint256:
        ret = self._steth.call(Abi.encode_with_signature("getPooledEthByShares(uint256)", ["uint256"], [shares]))
        return Abi.decode(["uint256"], ret)[0]

    def _steth_balance_to_shares(self, balance: uint256) -> uint256:
        ret = self._steth.call(Abi.encode_with_signature("getSharesByPooledEth(uint256)", ["uint256"], [balance]))
        return Abi.decode(["uint256"], ret)[0]

    def _provide_liquidity_eth(self, amount: uint256, provider: Account, beneficiary: Account) -> None:
        provider.balance += amount

        with default_chain.snapshot_and_revert():
            exchange_rate_timestamp = default_chain.blocks["latest"].timestamp
            ip_exchange_rate = self._calculate_ip_exchange_rate()

        tx = IAmmPoolsServiceStEth(self._router).provideLiquidityEth(beneficiary, amount, from_=provider, value=amount)
        assert tx.block.timestamp == exchange_rate_timestamp

        e = next(e for e in tx.events if isinstance(e, IAmmPoolsServiceStEth.ProvideLiquidityEth))
        steth_amount = e.amountStEth

        steth_shares = self._steth_balance_to_shares(steth_amount)

        expected_ip_amount = div(steth_amount * 10 ** 18, ip_exchange_rate)
        actual_ip_amount = div(steth_amount * 10 ** 18, e.exchangeRate)
        ip_error = abs(expected_ip_amount - actual_ip_amount)
        if ip_error > self._max_ip_error:
            self._max_ip_error = ip_error
            logger.warning(f"IP error {ip_error / 10 ** 18} ipstETH")

        self._balances[self._steth][self._steth_treasury] += steth_shares
        self._balances[self._ipst_eth][beneficiary] += actual_ip_amount

        logger.info(f"{beneficiary} provided {amount} ETH and received {self._balances[self._ipst_eth][beneficiary]} ipstETH")

    def _provide_liquidity(self, asset: IERC20Metadata, amount: uint256, provider: Account, beneficiary: Account) -> None:
        mint(asset, provider, amount)

        if asset == self._steth:
            # shares are minted actually, convert to balance
            self._balances[asset][provider] += amount
            amount = self._steth_shares_to_balance(amount)
        asset.approve(self._router, amount, from_=provider)

        with default_chain.snapshot_and_revert():
            exchange_rate_timestamp = default_chain.blocks["latest"].timestamp
            ip_exchange_rate = self._calculate_ip_exchange_rate()

        if asset == self._steth:
            tx = IAmmPoolsServiceStEth(self._router).provideLiquidityStEth(beneficiary, amount, from_=provider)
            e = next(e for e in tx.events if isinstance(e, IAmmPoolsServiceStEth.ProvideLiquidityStEth))
            steth_amount = amount
        elif asset == self._weth:
            tx = IAmmPoolsServiceStEth(self._router).provideLiquidityWEth(beneficiary, amount, from_=provider)
            e = next(e for e in tx.events if isinstance(e, IAmmPoolsServiceStEth.ProvideLiquidityEth))
            steth_amount = e.amountStEth
        else:
            raise ValueError("Unexpected asset")
        assert tx.block.timestamp == exchange_rate_timestamp

        steth_shares = self._steth_balance_to_shares(steth_amount)

        expected_ip_amount = div(steth_amount * 10 ** 18, ip_exchange_rate)
        actual_ip_amount = div(steth_amount * 10 ** 18, e.exchangeRate)
        ip_error = abs(expected_ip_amount - actual_ip_amount)
        if ip_error > self._max_ip_error:
            self._max_ip_error = ip_error
            logger.warning(f"IP error {ip_error / 10 ** 18} ipstETH")

        if asset == self._steth:
            self._balances[self._steth][provider] -= steth_shares
        self._balances[self._steth][self._steth_treasury] += steth_shares
        self._balances[self._ipst_eth][beneficiary] += actual_ip_amount

        logger.info(f"{beneficiary} provided {amount // 10 ** (18 - asset.decimals())} {asset.symbol()} and received {self._balances[self._ipst_eth][beneficiary]} ipstETH")

    @flow()
    def flow_redeem_liquidity(self):
        ipst_holders = [a for a in self._balances[self._ipst_eth].keys() if self._balances[self._ipst_eth][a] > 0 and a != default_chain.accounts[0]]
        if len(ipst_holders) == 0:
            return

        beneficiary = random_account()
        provider = random.choice(ipst_holders)
        amount = random_int(1, int(self._balances[self._ipst_eth][provider] * 1.1))

        with default_chain.snapshot_and_revert():
            exchange_rate_timestamp = default_chain.blocks["latest"].timestamp
            ip_exchange_rate = self._calculate_ip_exchange_rate()

            expected_steth_amount = div(ip_exchange_rate * amount, 10 ** 18)
            expected_steth_amount = div(expected_steth_amount * (10 ** 18 - self._redeem_fee_rate), 10 ** 18)

        with may_revert("IPOR_403") as e:
            tx = IAmmPoolsServiceStEth(self._router).redeemFromAmmPoolStEth(beneficiary, amount, from_=provider)
            assert tx.block.timestamp == exchange_rate_timestamp

        if amount > self._balances[self._ipst_eth][provider]:
            assert e.value is not None
            return
        else:
            assert e.value is None

        e = next(e for e in tx.events if isinstance(e, IAmmPoolsServiceStEth.RedeemStEth))
        actual_steth_amount = div(e.exchangeRate * amount, 10 ** 18)
        actual_steth_amount = div(actual_steth_amount * (10 ** 18 - self._redeem_fee_rate), 10 ** 18)
        actual_steth_shares = self._steth_balance_to_shares(actual_steth_amount)

        redeem_error = abs(actual_steth_amount - expected_steth_amount)
        if redeem_error > self._max_redeem_error:
            self._max_redeem_error = redeem_error
            logger.warning(f"Redeem error {redeem_error / 10 ** 18} stETH")

        self._balances[self._ipst_eth][provider] -= amount
        self._balances[self._steth][self._steth_treasury] -= actual_steth_shares
        self._balances[self._steth][beneficiary] += actual_steth_shares

        logger.info(f"{provider} redeemed {amount} ipstETH and received {actual_steth_amount} stETH for {beneficiary}")

    @flow()
    def flow_open_swap(self, tenor: IporTypes.SwapTenor):
        eth = IERC20Metadata("0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE")

        pay_fixed = random_bool()
        risk_indicators = self._risk_indicators[tenor][pay_fixed]
        max_leverage = risk_indicators.maxLeveragePerLeg
        leverage = random_int(self._min_leverage, max_leverage)
        asset = random.choice([self._steth, self._wsteth, self._weth, eth])
        opener = random_account()
        beneficiary = random_account(predicate=lambda a: a != default_chain.accounts[0])
        total_amount = random_int(1, 100) * 10 ** 18 + self._liquidation_deposit + self._publication_fee

        if asset != eth:
            mint(asset, opener, total_amount)
        else:
            opener.balance += total_amount

        if asset == self._wsteth:
            input_amount = total_amount
            total_amount = IwstEth(self._wsteth).getStETHByWstETH(total_amount)
        elif asset == self._steth:
            self._balances[self._steth][opener] += total_amount
            total_amount = self._steth_shares_to_balance(total_amount)
            input_amount = total_amount
        else:
            input_amount = total_amount

        available_amount = total_amount - self._liquidation_deposit - self._publication_fee

        tenor_length = self._get_tenor_length(tenor)

        collateral = div(available_amount * 10 ** 18, (10 ** 18 + div(leverage * self._opening_fee_rate * tenor_length, (365 * 10 ** 18))))
        opening_fee = available_amount - collateral
        opening_fee_treasury = div(opening_fee * self._opening_fee_treasury_portion_rate, 10 ** 18)
        notional = div(collateral * leverage, 10 ** 18)

        if asset != eth:
            asset.approve(self._router, input_amount, from_=opener)

        offered_rate_pay_fixed, offered_rate_receive_fixed = IAmmSwapsLens(self._router).getOfferedRate(
            self._steth, tenor, notional,
            self._risk_indicators[tenor][True],
            self._risk_indicators[tenor][False],
            request_type="tx"
        ).return_value

        if pay_fixed:
            offered_rate = offered_rate_pay_fixed
            # add a small margin, contract will use current rate which can be slightly different
            acceptable_rate = math.ceil(offered_rate * 1.01)
        else:
            offered_rate = offered_rate_receive_fixed
            # add a small margin, contract will use current rate which can be slightly different
            acceptable_rate = math.floor(offered_rate * 0.99)

        if not pay_fixed and acceptable_rate <= 0:
            if asset == eth:
                self._eth_balances[opener] += input_amount
            elif asset != self._steth:
                self._balances[asset][opener] += input_amount
            self.invariant_balances()
            self.invariant_eth_balances()
            return

        open_swap_function = self._open_swap_functions[tenor][pay_fixed]
        if asset == eth:
            tx = open_swap_function(beneficiary, asset, input_amount, acceptable_rate, leverage, risk_indicators, from_=opener, value=total_amount)
        else:
            tx = open_swap_function(beneficiary, asset, input_amount, acceptable_rate, leverage, risk_indicators, from_=opener)
        swap_id = tx.return_value

        e = next(e for e in tx.events if isinstance(e, SwapEventsBaseV1.OpenSwap))
        assert e.amounts.inputAssetTotalAmount == input_amount
        assert e.amounts.assetTotalAmount == total_amount
        assert e.amounts.collateral == collateral
        assert e.amounts.notional == notional

        if pay_fixed:
            assert e.indicator.fixedInterestRate <= acceptable_rate
        else:
            assert e.indicator.fixedInterestRate >= acceptable_rate

        expected_ibt_price = self._get_ibt_price(tx.block.timestamp)
        actual_ibt_price = self._oracle.getAccruedIndex(tx.block.timestamp, self._steth).ibtPrice
        expected_ibt_quantity = div(notional * 10 ** 18, expected_ibt_price)
        actual_ibt_quantity = div(notional * 10 ** 18, actual_ibt_price)

        error = abs(expected_ibt_quantity - actual_ibt_quantity)
        if error > self._max_ibt_quantity_error:
            self._max_ibt_quantity_error = error
            logger.warning(f"IBT quantity error {error / 10 ** 18} IBT")

        self._swaps[swap_id] = Swap(
            beneficiary,
            collateral,
            notional,
            leverage,
            e.indicator.fixedInterestRate,
            actual_ibt_quantity,
            pay_fixed,
            tx.block.timestamp,
            tenor,
        )

        if asset == self._steth:
            self._balances[self._steth][opener] -= self._steth_balance_to_shares(total_amount)
        self._balances[self._steth][self._steth_treasury] += self._steth_balance_to_shares(total_amount)
        self._ipor_treasury += opening_fee_treasury

        symbol = "ETH" if asset == eth else asset.symbol()
        if pay_fixed:
            logger.info(f"{beneficiary.label} opened pay fixed swap {swap_id} in {symbol} with rate {e.indicator.fixedInterestRate / 10 ** 16}% and notional {notional / 10 ** 18} stETH")
        else:
            logger.info(f"{beneficiary.label} opened receive fixed swap {swap_id} in {symbol} with rate {e.indicator.fixedInterestRate / 10 ** 16}% and notional {notional / 10 ** 18} stETH")

    @flow()
    def flow_close_swap(self):
        if len(self._swaps) == 0:
            return

        swap_id = random.choice(list(self._swaps.keys()))
        self._close_swap(swap_id)

    def _close_swap(self, swap_id: uint32):
        swap = self._swaps[swap_id]
        beneficiary = random_account()
        tenor_length = self._get_tenor_length(swap.tenor)

        close_swap_risk_indicators = AmmTypes.CloseSwapRiskIndicatorsInput(
            self._risk_indicators[swap.tenor][True],
            self._risk_indicators[swap.tenor][False],
        )

        with default_chain.snapshot_and_revert():
            default_chain.mine()
            offered_rates_block = default_chain.blocks["latest"]
            offered_pay_fixed, offered_receive_fixed = IAmmSwapsLens(self._router).getOfferedRate(
                self._steth, swap.tenor, swap.notional,
                self._risk_indicators[swap.tenor][True],
                self._risk_indicators[swap.tenor][False],
            )
            if swap.pay_fixed:
                pnl = IAmmSwapsLens(self._router).getPnlPayFixed(self._steth, swap_id)
            else:
                pnl = IAmmSwapsLens(self._router).getPnlReceiveFixed(self._steth, swap_id)

            close_swap_details = IAmmCloseSwapLens(self._router).getClosingSwapDetails(
                self._steth,
                swap.buyer,
                AmmTypes.SwapDirection.PAY_FIXED_RECEIVE_FLOATING if swap.pay_fixed
                else AmmTypes.SwapDirection.PAY_FLOATING_RECEIVE_FIXED,
                swap_id,
                offered_rates_block.timestamp,
                close_swap_risk_indicators,
            )

        default_chain.set_next_block_timestamp(offered_rates_block.timestamp)
        pending_timestamp = default_chain.blocks["pending"].timestamp
        remaining_time = swap.open_timestamp + tenor_length * 24 * 60 * 60 - pending_timestamp
        min_liquidation_threshold_buyer = div(swap.collateral * self._min_liquidation_threshold_buyer, 10 ** 18)
        min_liquidation_threshold_community = div(swap.collateral * self._min_liquidation_threshold_community, 10 ** 18)

        if 0 < remaining_time <= self._time_before_maturity_community or (abs(pnl) >= min_liquidation_threshold_community and abs(pnl) != swap.collateral):
            closer = random_account(predicate=lambda a: a != default_chain.accounts[0])  # anyone except contract owner
            can_close = True
        else:
            closer = swap.buyer
            can_close = pending_timestamp > swap.open_timestamp + self._time_after_open_wihout_unwinding

        with may_revert("IPOR_341") as e:
            tx = IAmmCloseSwapServiceStEth(self._router).closeSwapsStEth(
                beneficiary,
                [swap_id] if swap.pay_fixed else [],
                [swap_id] if not swap.pay_fixed else [],
                close_swap_risk_indicators,
                from_=closer,
            )
            assert tx.block.timestamp == pending_timestamp
            assert tx.block.number == offered_rates_block.number
            assert tx.block.timestamp == offered_rates_block.timestamp

        assert (e.value is None) == can_close
        if not can_close:
            assert close_swap_details.closableStatus == AmmTypes.SwapClosableStatus.SWAP_CANNOT_CLOSE_WITH_UNWIND_ACTION_IS_TOO_EARLY
            return

        if swap.pay_fixed:
            assert tx.return_value[0] == [AmmTypes.IporSwapClosingResult(swap_id, True)]
        else:
            assert tx.return_value[1] == [AmmTypes.IporSwapClosingResult(swap_id, True)]

        must_unwind = not (
            remaining_time <= self._time_before_maturity_buyer or
            abs(pnl) >= min_liquidation_threshold_buyer
        )

        if not must_unwind:
            expected_pnl = self._calculate_pnl_raw(swap, tx.block.number)
            unwinding_fee = 0
            actual_unwinding_fee = 0
        else:
            #unwind
            unwind_events = [e for e in tx.events if isinstance(e, AmmEventsBaseV1.SwapUnwind)]
            assert len(unwind_events) == 1
            actual_unwinding_fee = unwind_events[0].unwindFeeLPAmount + unwind_events[0].unwindFeeTreasuryAmount

            unwinding_fee = round(swap.notional * self._unwinding_fee_rate / 10 ** 18 * remaining_time / (365 * 24 * 60 * 60))
            if swap.pay_fixed:
                unwind_pnl = (
                    round(swap.notional * math.exp(offered_receive_fixed / 10 ** 18 * remaining_time / (365 * 24 * 60 * 60)))
                    - round(swap.notional * math.exp(swap.fixed_rate / 10 ** 18 * remaining_time / (365 * 24 * 60 * 60)))
                )
            else:
                unwind_pnl = (
                    round(swap.notional * math.exp(swap.fixed_rate / 10 ** 18 * remaining_time / (365 * 24 * 60 * 60)))
                    - round(swap.notional * math.exp(offered_pay_fixed / 10 ** 18 * remaining_time / (365 * 24 * 60 * 60)))
                )

            if unwind_pnl < -swap.collateral:
                unwind_pnl = -swap.collateral
            elif unwind_pnl > swap.collateral:
                unwind_pnl = swap.collateral

            expected_pnl = unwind_pnl + self._calculate_pnl_raw(swap, tx.block.number)
            if expected_pnl < -swap.collateral:
                expected_pnl = -swap.collateral
            elif expected_pnl > swap.collateral:
                expected_pnl = swap.collateral

            if swap.collateral + expected_pnl <= unwinding_fee:
                raise AssertionError("Should have reverted")

            expected_pnl -= unwinding_fee

        unwinding_fee_treasury = div(actual_unwinding_fee * self._unwinding_fee_treasury_portion_rate, 10 ** 18)
        self._ipor_treasury += unwinding_fee_treasury
        close_swap_event = next(e for e in tx.events if isinstance(e, AmmEventsBaseV1.CloseSwap))

        actual_payoff = close_swap_event.transferredToBuyer
        expected_payoff = swap.collateral + expected_pnl
        if swap.buyer == beneficiary:
            expected_payoff += self._liquidation_deposit

        error = abs(expected_payoff - actual_payoff)
        if error > self._max_payoff_error:
            self._max_payoff_error = error
            logger.error(f"Close swap payoff error {error / 10 ** 18} stETH")

        # test IAmmCloseSwapLens
        assert close_swap_details.swapUnwindRequired == must_unwind
        assert close_swap_details.swapUnwindOpeningFeeAmount == actual_unwinding_fee
        assert close_swap_details.swapUnwindFeeTreasuryAmount == unwinding_fee_treasury
        assert close_swap_details.swapUnwindFeeLPAmount == actual_unwinding_fee - unwinding_fee_treasury

        actual_payoff_shares = self._steth_balance_to_shares(actual_payoff)

        if swap.buyer == beneficiary:
            self._balances[self._steth][self._steth_treasury] -= actual_payoff_shares
            self._balances[self._steth][swap.buyer] += actual_payoff_shares
        else:
            liquidation_deposit_shares = self._steth_balance_to_shares(self._liquidation_deposit)

            self._balances[self._steth][self._steth_treasury] -= actual_payoff_shares + liquidation_deposit_shares
            self._balances[self._steth][swap.buyer] += actual_payoff_shares
            self._balances[self._steth][beneficiary] += liquidation_deposit_shares

        self._closed_swaps[swap_id] = swap
        del self._swaps[swap_id]

        logger.info(f"{closer.label} closed swap {swap_id}")

    @invariant()
    def invariant_balances(self):
        # stETH balances are stored in the form of shares
        for account, balance in self._balances[self._steth].items():
            data = self._steth.call(Abi.encode_with_signature("sharesOf(address)", ["address"], [account]))
            shares = Abi.decode(["uint256"], data)[0]
            assert shares == balance

        for token in self._balances.keys():
            if token != self._steth:
                for account, balance in self._balances[token].items():
                    assert token.balanceOf(account) == balance

    @invariant()
    def invariant_eth_balances(self):
        for account, balance in self._eth_balances.items():
            assert account.balance == balance

    @invariant()
    def invariant_ipor_treasury(self):
        assert self._steth_storage.getBalance().treasury == self._ipor_treasury

    @invariant()
    def invariant_soap(self):
        soap_pay_fixed, soap_receive_fixed, _ = IAmmSwapsLens(self._router).getSoap(self._steth)
        expected_soap_pay_fixed, expected_soap_receive_fixed = self._calculate_soap()
        pay_fixed_error = abs(expected_soap_pay_fixed - soap_pay_fixed)
        receive_fixed_error = abs(expected_soap_receive_fixed - soap_receive_fixed)
        error = max(receive_fixed_error, pay_fixed_error)

        if error > self._max_soap_error:
            self._max_soap_error = error
            logger.warning(f"SOAP error {error / 10 ** 18} stETH")

    @invariant()
    def invariant_ip_exchange_rate(self):
        tx = AmmPoolsLensStEth(self._router).getIpstEthExchangeRate(request_type="tx")
        exchange_rate = tx.return_value
        expected_exchange_rate = self._calculate_ip_exchange_rate()
        rel_error = abs(exchange_rate - expected_exchange_rate) / expected_exchange_rate

        if rel_error > self._max_ip_exchange_rate_error:
            self._max_ip_exchange_rate_error = rel_error
            logger.warning(f"Exchange rate error {rel_error * 100}%")

    @invariant()
    def invariant_pnl(self):
        for swap_id, swap in self._swaps.items():
            if swap.pay_fixed:
                tx = IAmmSwapsLens(self._router).getPnlPayFixed(self._steth, swap_id, request_type="tx")
                pnl = tx.return_value
            else:
                tx = IAmmSwapsLens(self._router).getPnlReceiveFixed(self._steth, swap_id, request_type="tx")
                pnl = tx.return_value

            closing_block = default_chain.blocks["latest"]
            expected_pnl = self._calculate_pnl_raw(swap, closing_block.number)

            error = abs(expected_pnl - pnl)
            if error > self._max_pnl_error:
                self._max_pnl_error = error
                logger.error(f"PnL error: expected {expected_pnl} actual {pnl} difference {error / 10 ** 18} stETH")


@default_chain.connect(fork=FORK_URL)
@on_revert(lambda e: print(e.tx.call_trace if e.tx else "Revert in call"))
def test_steth_fuzz():
    for label, account in zip(names, default_chain.accounts):
        account.label = label

    StETHFuzzTest().run(10, 10_000)
