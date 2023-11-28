import logging
import math
import random
from bisect import bisect_right
from dataclasses import dataclass
import time
from typing import Callable, Any, Dict, Set, Tuple

from wake.testing import *
from wake.testing.fuzzing import *
from pytypes.source.contracts.interfaces.IAmmCloseSwapLens import IAmmCloseSwapLens
from pytypes.source.contracts.interfaces.IAmmCloseSwapService import IAmmCloseSwapService
from pytypes.source.contracts.interfaces.IAmmGovernanceService import IAmmGovernanceService
from pytypes.source.contracts.interfaces.IAmmOpenSwapService import IAmmOpenSwapService
from pytypes.source.contracts.interfaces.IAmmPoolsLens import IAmmPoolsLens
from pytypes.source.contracts.interfaces.IAmmPoolsService import IAmmPoolsService
from pytypes.source.contracts.interfaces.IAmmStorage import IAmmStorage
from pytypes.source.contracts.interfaces.IAmmSwapsLens import IAmmSwapsLens
from pytypes.source.contracts.interfaces.IAssetManagement import IAssetManagement
from pytypes.source.contracts.interfaces.IAssetManagementLens import IAssetManagementLens
from pytypes.source.contracts.interfaces.types.AmmTypes import AmmTypes
from pytypes.source.contracts.interfaces.types.IporRiskManagementOracleTypes import IporRiskManagementOracleTypes
from pytypes.source.contracts.interfaces.types.IporTypes import IporTypes
from pytypes.source.contracts.oracles.IporOracle import IporOracle
from pytypes.source.contracts.oracles.IporRiskManagementOracle import IporRiskManagementOracle
from pytypes.source.contracts.router.IporProtocolRouter import IporProtocolRouter
from pytypes.openzeppelin.contracts.token.ERC20.extensions.IERC20Metadata import IERC20Metadata

from .config import FORK_URL
from .setup import setup_router, get_dai, get_usdc, get_usdt, get_oracle, get_risk_oracle
from .utils import mint


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

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
    asset: IERC20Metadata
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


class IporFuzzTest(FuzzTest):
    _liquidation_deposit: uint256  # in 18 decimals
    _publication_fee: uint256  # in 18 decimals
    _opening_fee_rate: uint256  # in 18 decimals
    _opening_fee_treasury_portion_rate: uint256  # in 18 decimals
    _unwinding_fee_rate: uint256  # in 18 decimals
    _unwinding_fee_treasury_portion_rate: uint256  # in 18 decimals
    _redeem_fee_rate: uint256  # in 18 decimals
    _min_leverage: uint256  # in 18 decimals
    _time_before_maturity_community: uint256  # in seconds
    _time_before_maturity_buyer: uint256  # in seconds
    _min_liquidation_threshold_community: uint256  # in 18 decimals
    _min_liquidation_threshold_buyer: uint256  # in 18 decimals
    _treasury_asset_management_ratio: uint256  # in 18 decimals
    _auto_rebalance_threshold: uint256  # in 18 decimals

    _router: IporProtocolRouter
    _oracle: IporOracle
    _risk_oracle: IporRiskManagementOracle
    _dai: IERC20Metadata
    _usdc: IERC20Metadata
    _usdt: IERC20Metadata
    _ip_tokens: Dict[IERC20Metadata, IERC20Metadata]
    _treasuries: Dict[IERC20Metadata, Account]
    _storages: Dict[IERC20Metadata, IAmmStorage]
    _open_swap_functions: Dict[IporTypes.SwapTenor, Dict[IERC20Metadata, Dict[bool, Callable]]]
    _close_swap_functions: Dict[IERC20Metadata, Callable]
    _ipor_indexes: Dict[IERC20Metadata, List[uint256]]

    _times: List[uint256]  # IPOR index update times so that _times[0] is timestamp of _ipor_indexes[0] update

    _swaps: Dict[IERC20Metadata, Dict[uint32, Swap]]
    _balances: Dict[IERC20Metadata, Dict[Account, uint256]]
    _ip_balances: Dict[IERC20Metadata, Dict[Account, uint256]]  # Ip token balances
    _treasury_balances: Dict[IERC20Metadata, uint256]  # the part of _lp_balances that is kept in treasury and not sent to asset management
    _ipor_treasury_balances: Dict[IERC20Metadata, uint256]
    _closed_swaps: Dict[IERC20Metadata, Dict[uint32, Swap]]
    _appointed_to_rebalance: Dict[IERC20Metadata, Set[Account]]

    _max_payoff_error: int
    _max_ip_exchange_rate_error: float
    _max_soap_error: int
    _max_redeem_error: int
    _max_asset_management_error: int
    _max_treasury_error: int
    _max_non_lp_balance_error: int
    _max_ipor_treasury_error: int

    def pre_sequence(self) -> None:
        self._max_payoff_error = 0
        self._max_ip_exchange_rate_error = 0
        self._max_soap_error = 0
        self._max_redeem_error = 0
        self._max_asset_management_error = 0
        self._max_treasury_error = 0
        self._max_non_lp_balance_error = 0
        self._max_ipor_treasury_error = 0

        self._liquidation_deposit = random_int(1, 30) * 10 ** 18
        self._publication_fee = random_int(1, 10) * 10 ** 18
        self._opening_fee_rate = random_int(1, 20) * 10 ** 15  # 0.1% - 2%
        self._opening_fee_treasury_portion_rate = random_int(1, 20) * 10 ** 15  # 0.1% - 2%
        self._unwinding_fee_rate = random_int(1, 20) * 10 ** 15  # 0.1% - 2%
        self._unwinding_fee_treasury_portion_rate = random_int(1, 20) * 10 ** 15  # 0.1% - 2%
        self._redeem_fee_rate = random_int(1, 10) * 10 ** 15  # 0.1% - 1%
        self._min_leverage = 10 * 10 ** 18  # 10x
        self._time_before_maturity_community = 1 * 60 * 60  # 1 hour
        self._time_before_maturity_buyer = 24 * 60 * 60  # 24 hours
        self._min_liquidation_threshold_community = 995 * 10 ** 15  # 99.5%
        self._min_liquidation_threshold_buyer = 990 * 10 ** 15  # 99%
        self._treasury_asset_management_ratio = random_int(50, 95) * 10 ** 16  # 50% - 95%, max resolution 4 decimals
        self._auto_rebalance_threshold = 7_000 * 10 ** 18  # 7_000 USD

        self._router = setup_router(
            liquidation_deposit=self._liquidation_deposit // 10 ** 18,
            publication_fee=self._publication_fee,
            opening_fee_rate=self._opening_fee_rate,
            opening_fee_treasury_portion_rate=self._opening_fee_treasury_portion_rate,
            unwinding_fee_rate=self._unwinding_fee_rate,
            unwinding_fee_treasury_portion_rate=self._unwinding_fee_treasury_portion_rate,
            min_leverage=self._min_leverage,
            time_before_maturity_community=self._time_before_maturity_community,
            time_before_maturiy_buyer=self._time_before_maturity_buyer,
            min_liquidation_threshold_community=self._min_liquidation_threshold_community,
            min_liquidation_threshold_buyer=self._min_liquidation_threshold_buyer,
            redeem_fee_rate=self._redeem_fee_rate,
        )
        self._oracle = get_oracle()
        self._oracle.addUpdater(default_chain.accounts[0])

        self._risk_oracle = get_risk_oracle()
        self._risk_oracle.addUpdater(default_chain.accounts[0])

        self._dai = get_dai()
        self._usdc = get_usdc()
        self._usdt = get_usdt()
        self._ip_tokens = {
            asset: IERC20Metadata(IAmmPoolsLens(self._router).getAmmPoolsLensConfiguration(asset).ipToken)
            for asset in [self._dai, self._usdc, self._usdt]
        }

        self._treasuries = {}
        self._storages = {}

        self._swaps = {
            self._dai: {},
            self._usdc: {},
            self._usdt: {},
        }
        self._balances = {
            self._dai: {},
            self._usdc: {},
            self._usdt: {},
        }
        self._ip_balances = {
            self._ip_tokens[self._dai]: {},
            self._ip_tokens[self._usdc]: {},
            self._ip_tokens[self._usdt]: {},
        }
        self._treasury_balances = {
            self._dai: 0,
            self._usdc: 0,
            self._usdt: 0,
        }
        self._ipor_treasury_balances = {
            self._dai: 0,
            self._usdc: 0,
            self._usdt: 0,
        }
        self._closed_swaps = {
            self._dai: {},
            self._usdc: {},
            self._usdt: {},
        }
        self._appointed_to_rebalance = {
            self._dai: set(),
            self._usdc: set(),
            self._usdt: set(),
        }

        for token in [self._dai, self._usdc, self._usdt]:
            info = IAmmPoolsLens(self._router).getAmmPoolsLensConfiguration(token)
            self._balances[token][Account(info.ammTreasury)] = 0
            self._treasuries[token] = Account(info.ammTreasury)
            self._storages[token] = IAmmStorage(info.ammStorage)

            for account in default_chain.accounts:
                balance = token.balanceOf(account)
                if balance > 0:
                    token.transfer(Address(1), balance, from_=account)
                self._balances[token][account] = 0

        for ip_token in self._ip_tokens.values():
            for account in default_chain.accounts:
                assert ip_token.balanceOf(account) == 0
                self._ip_balances[ip_token][account] = 0

        self._open_swap_functions = {
            IporTypes.SwapTenor.DAYS_28: {
                self._dai: {
                    True: IAmmOpenSwapService(self._router).openSwapPayFixed28daysDai,
                    False: IAmmOpenSwapService(self._router).openSwapReceiveFixed28daysDai,
                },
                self._usdc: {
                    True: IAmmOpenSwapService(self._router).openSwapPayFixed28daysUsdc,
                    False: IAmmOpenSwapService(self._router).openSwapReceiveFixed28daysUsdc,
                },
                self._usdt: {
                    True: IAmmOpenSwapService(self._router).openSwapPayFixed28daysUsdt,
                    False: IAmmOpenSwapService(self._router).openSwapReceiveFixed28daysUsdt,
                },
            },
            IporTypes.SwapTenor.DAYS_60: {
                self._dai: {
                    True: IAmmOpenSwapService(self._router).openSwapPayFixed60daysDai,
                    False: IAmmOpenSwapService(self._router).openSwapReceiveFixed60daysDai,
                },
                self._usdc: {
                    True: IAmmOpenSwapService(self._router).openSwapPayFixed60daysUsdc,
                    False: IAmmOpenSwapService(self._router).openSwapReceiveFixed60daysUsdc,
                },
                self._usdt: {
                    True: IAmmOpenSwapService(self._router).openSwapPayFixed60daysUsdt,
                    False: IAmmOpenSwapService(self._router).openSwapReceiveFixed60daysUsdt,
                },
            },
            IporTypes.SwapTenor.DAYS_90: {
                self._dai: {
                    True: IAmmOpenSwapService(self._router).openSwapPayFixed90daysDai,
                    False: IAmmOpenSwapService(self._router).openSwapReceiveFixed90daysDai,
                },
                self._usdc: {
                    True: IAmmOpenSwapService(self._router).openSwapPayFixed90daysUsdc,
                    False: IAmmOpenSwapService(self._router).openSwapReceiveFixed90daysUsdc,
                },
                self._usdt: {
                    True: IAmmOpenSwapService(self._router).openSwapPayFixed90daysUsdt,
                    False: IAmmOpenSwapService(self._router).openSwapReceiveFixed90daysUsdt,
                },
            },
        }
        self._close_swap_functions = {
            self._dai: IAmmCloseSwapService(self._router).closeSwapsDai,
            self._usdc: IAmmCloseSwapService(self._router).closeSwapsUsdc,
            self._usdt: IAmmCloseSwapService(self._router).closeSwapsUsdt,
        }

        # set pools params
        for asset in [self._dai, self._usdc, self._usdt]:
            IAmmGovernanceService(self._router).setAmmPoolsParams(
                asset,
                100_000_000,  # max amount of liquidity pool balance in USD (without decimals)
                10_000_000,  # max amount of USD a single user can deposit
                self._auto_rebalance_threshold // 10 ** 21,  # auto rebalance threshold in thousands of USD
                self._treasury_asset_management_ratio // 10 ** 14,  # treasury asset management ratio
            )

        # start with real ipor indexes
        real_oracle = IporOracle("0x421C69EAa54646294Db30026aeE80D01988a6876")
        self._ipor_indexes = {
            self._dai: [real_oracle.getIndex(self._dai)[0]],
            self._usdc: [real_oracle.getIndex(self._usdc)[0]],
            self._usdt: [real_oracle.getIndex(self._usdt)[0]],
        }
        tx = self._oracle.updateIndexes(
            [self._dai, self._usdc, self._usdt],
            [self._ipor_indexes[self._dai][0], self._ipor_indexes[self._usdc][0], self._ipor_indexes[self._usdt][0]],
        )
        self._times = [tx.block.timestamp]

        # provide initial liquidity
        self.start_timestamp = default_chain.blocks["latest"].timestamp
        a = default_chain.accounts[0]
        for asset in [self._dai, self._usdc, self._usdt]:
            self._provide_liquidity(asset, 1_000_000 * 10 ** 18, a, a)

        logger.debug("Setup complete")

    # unused, kept for reference
    def _calculate_pnl(self, swap: Swap, block: int):
        payoff_timestamp = default_chain.blocks[block].timestamp
        accrued = self._oracle.getAccruedIndex(payoff_timestamp, swap.asset, block=block)
        delta_time = payoff_timestamp - swap.open_timestamp

        interest_fixed = swap.notional / 10 ** 18 * math.exp(swap.fixed_rate / 10 ** 18 * delta_time / (365 * 24 * 60 * 60))
        interest_fixed_wad = round(interest_fixed * 10 ** 18)
        interest_floating_wad = div(swap.ibt_quantity * accrued.ibtPrice, 10 ** 18)

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
            interest_floating = swap.notional / 10 ** 18 * math.exp(self._ipor_indexes[swap.asset][start_index] / 10 ** 18 * delta_time / (365 * 24 * 60 * 60))
        else:
            interest_floating = swap.notional / 10 ** 18 * math.exp(self._ipor_indexes[swap.asset][start_index] / 10 ** 18 * (self._times[start_index + 1] - swap.open_timestamp) / (365 * 24 * 60 * 60))
            for i in range(start_index + 1, end_index):
                interest_floating *= math.exp(self._ipor_indexes[swap.asset][i] / 10 ** 18 * (self._times[i + 1] - self._times[i]) / (365 * 24 * 60 * 60))
            interest_floating *= math.exp(self._ipor_indexes[swap.asset][end_index] / 10 ** 18 * (payoff_timestamp - self._times[end_index]) / (365 * 24 * 60 * 60))

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
    def _calculate_soap(self, asset: IERC20Metadata):
        expected_soap_pay_fixed = 0
        expected_soap_receive_fixed = 0
        latest_block = default_chain.blocks["latest"].number

        for swap in self._swaps[asset].values():
            if swap.pay_fixed:
                expected_soap_pay_fixed += self._calculate_pnl_raw(swap, latest_block)
            else:
                expected_soap_receive_fixed += self._calculate_pnl_raw(swap, latest_block)

        return expected_soap_pay_fixed, expected_soap_receive_fixed

    # IMPORTANT: must be called in the context of the latest block - we do not keep history of all swaps
    def _calculate_ip_exchange_rate(self, asset: IERC20Metadata):
        total_supply = self._ip_tokens[asset].totalSupply()

        if total_supply == 0:
            return 10 ** 18
        else:
            # have to use lens instead of self._lp_balance because of interest from AAVE and Compound
            return div((IAmmPoolsLens(self._router).getAmmBalance(asset).liquidityPool - sum(self._calculate_soap(asset))) * 10 ** 18, total_supply)

    def _get_tenor_length(self, tenor: IporTypes.SwapTenor) -> int:
        if tenor == IporTypes.SwapTenor.DAYS_28:
            return 28
        elif tenor == IporTypes.SwapTenor.DAYS_60:
            return 60
        elif tenor == IporTypes.SwapTenor.DAYS_90:
            return 90
        else:
            raise ValueError("Invalid tenor")

    def post_sequence(self) -> None:
        self.print_all_errors()
        #for asset in [self._dai, self._usdc, self._usdt]:
            #plt.plot(self._times, self._ipor_indexes[asset], label=asset.symbol())
            #plt.show()

    def pre_flow(self, flow: Callable[..., Any]) -> None:
        # update IPOR indexes
        for asset in [self._dai, self._usdc, self._usdt]:
            add = random_bool()
            difference = random_int(5 * 10 ** 14, 25 * 10 ** 14)  # 0.05% - 2.25%

            # must be positive
            if not add and self._ipor_indexes[asset][-1] <= difference:
                add = True

            # must be less than 10%
            if add and self._ipor_indexes[asset][-1] + difference > 10 ** 17:
                add = False

            if not add:
                difference = -difference
            ipor_index = self._ipor_indexes[asset][-1] + difference
            self._ipor_indexes[asset].append(ipor_index)

            p = min(20, len(self._ipor_indexes[asset]))

            receive_fixed_spread = -random_int(1 * 10 ** 3, 5 * 10 ** 3)  # 0.1% - 0.5%
            pay_fixed_spread = (sum(self._ipor_indexes[asset][-p:]) // p - ipor_index) // 10 ** 12
            if pay_fixed_spread < 0:
                pay_fixed_spread += random_int(1 * 10 ** 3, 3 * 10 ** 3)
            min_pay_fixed_rate = 10  # 0.1%
            max_receive_fixed_rate = 1000  # 10%
            self._risk_oracle.updateBaseSpreadsAndFixedRateCaps(asset, IporRiskManagementOracleTypes.BaseSpreadsAndFixedRateCaps(
                pay_fixed_spread, receive_fixed_spread,
                pay_fixed_spread, receive_fixed_spread,
                pay_fixed_spread, receive_fixed_spread,
                min_pay_fixed_rate, max_receive_fixed_rate,
                min_pay_fixed_rate, max_receive_fixed_rate,
                min_pay_fixed_rate, max_receive_fixed_rate,
            ))

        tx = self._oracle.updateIndexes(
            list(self._ipor_indexes.keys()),
            [self._ipor_indexes[asset][-1] for asset in self._ipor_indexes.keys()]
        )
        self._times.append(tx.block.timestamp)

    def pre_invariants(self) -> None:
        latest_timestamp = default_chain.blocks["latest"].timestamp

        # close all swaps that expired
        swaps_to_close = []
        for asset in [self._dai, self._usdc, self._usdt]:
            for swap_id, swap in self._swaps[asset].items():
                if swap.open_timestamp + self._get_tenor_length(swap.tenor) * 24 * 60 * 60 < latest_timestamp:
                    # swap has expired, close it
                    swaps_to_close.append((asset, swap_id))

        for asset, swap_id in swaps_to_close:
            self.close_swap(asset, swap_id)

    def post_invariants(self) -> None:
        # roll forward time
        time_change = random_int(1 * 24 * 60 * 60, 20 * 24 * 60 * 60)  # 1-20 days
        default_chain.mine(lambda x: x + time_change)

    @flow()
    def flow_provide_liquidity(self) -> None:
        provider = random_account()
        beneficiary = random_account(predicate=lambda a: a != default_chain.accounts[0])
        asset = random.choice([self._dai, self._usdc, self._usdt])
        usd_amount = random_int(1, 10_000)
        amount = usd_amount * 10 ** asset.decimals()
        amount_wad = amount * 10 ** (18 - asset.decimals())

        self._provide_liquidity(asset, amount_wad, provider, beneficiary)

    def _provide_liquidity(self, asset: IERC20Metadata, amount_wad: uint256, provider: Account, beneficiary: Account) -> None:
        amount = amount_wad // 10 ** (18 - asset.decimals())
        mint(asset, provider, amount)
        asset.approve(self._router, amount, from_=provider)

        with default_chain.snapshot_and_revert():
            ip_balance_timestamp = default_chain.blocks["latest"].timestamp
            ip_token = self._ip_tokens[asset]
            ip_balance = div(amount_wad * 10 ** 18, self._calculate_ip_exchange_rate(asset))

            vault_wad = IAssetManagementLens(self._router).balanceOfAmmTreasuryInAssetManagement(asset)
            treasury_wad = self._balances[asset][self._treasuries[asset]] * 10 ** (18 - asset.decimals())
            rebalance_amount_wad = div_int((treasury_wad + amount_wad + vault_wad) * (10 ** 18 - self._treasury_asset_management_ratio), 10 ** 18) - vault_wad

        if asset == self._dai:
            func = IAmmPoolsService(self._router).provideLiquidityDai
        elif asset == self._usdc:
            func = IAmmPoolsService(self._router).provideLiquidityUsdc
        else:
            func = IAmmPoolsService(self._router).provideLiquidityUsdt

        with may_revert("IPOR_322") as e:
            tx = func(beneficiary, amount, from_=provider)
            assert tx.block.timestamp == ip_balance_timestamp

        if e.value is not None:
            mint(asset, provider, -amount)
            asset.approve(self._router, 0, from_=provider)
            return

        self._balances[asset][self._treasuries[asset]] += amount_wad // 10 ** (18 - asset.decimals())
        self._ip_balances[ip_token][beneficiary] += ip_balance
        self._treasury_balances[asset] += amount_wad

        # rebalance
        if rebalance_amount_wad > 0 and self._auto_rebalance_threshold > 0 and amount_wad > self._auto_rebalance_threshold:
            rebalance_amount = div(rebalance_amount_wad, 10 ** (18 - asset.decimals()))
            self._balances[asset][self._treasuries[asset]] -= rebalance_amount
            self._treasury_balances[asset] -= rebalance_amount_wad

        logger.info(f"{beneficiary.label} provided ${amount_wad // 10 ** (18 - asset.decimals())} {asset.symbol()} and received {self._ip_balances[ip_token][beneficiary]} {ip_token.symbol()}")

    @flow(weight=90)
    def flow_redeem_liquidity(self) -> None:
        assets = [asset for asset, ip_token in self._ip_tokens.items() if sum(self._ip_balances[ip_token][a] for a in self._ip_balances[ip_token].keys() if a != default_chain.accounts[0]) > 0]
        if len(assets) == 0:
            return
        asset = random.choice(assets)
        ip_token = self._ip_tokens[asset]
        provider = random.choice([a for a in self._ip_balances[ip_token].keys() if self._ip_balances[ip_token][a] > 0 and a != default_chain.accounts[0]])
        beneficiary = random_account()
        # redeem all
        amount = ip_token.balanceOf(provider)

        with default_chain.snapshot_and_revert():
            exchange_rate_timestamp = default_chain.blocks["latest"].timestamp
            exchange_rate = IAmmPoolsLens(self._router).getIpTokenExchangeRate(asset)
            expected_asset_amount_wad = div(
                self._ip_balances[ip_token][provider] * self._calculate_ip_exchange_rate(asset),
                10 ** 18
            )
            expected_redeem_fee_wad = div(expected_asset_amount_wad * self._redeem_fee_rate, 10 ** 18)
            expected_redeem_amount_wad = expected_asset_amount_wad - expected_redeem_fee_wad
            asset_amount_wad = div(amount * exchange_rate, 10 ** 18)
            redeem_fee_wad = div(asset_amount_wad * self._redeem_fee_rate, 10 ** 18)
            redeem_amount_wad = asset_amount_wad - redeem_fee_wad
            redeem_amount = div(redeem_amount_wad, 10 ** (18 - asset.decimals()))
            redeem_amount_wad = redeem_amount * 10 ** (18 - asset.decimals())

            vault_wad = IAssetManagementLens(self._router).balanceOfAmmTreasuryInAssetManagement(asset)
            treasury_wad = self._balances[asset][self._treasuries[asset]] * 10 ** (18 - asset.decimals())
            rebalance_amount_wad = div_int((treasury_wad - redeem_amount_wad + vault_wad) * (10**18 - self._treasury_asset_management_ratio), 10**18) - vault_wad

        if asset == self._dai:
            func = IAmmPoolsService(self._router).redeemFromAmmPoolDai
        elif asset == self._usdc:
            func = IAmmPoolsService(self._router).redeemFromAmmPoolUsdc
        else:
            func = IAmmPoolsService(self._router).redeemFromAmmPoolUsdt
        tx = func(beneficiary, amount, from_=provider)
        assert tx.block.timestamp == exchange_rate_timestamp

        # rebalance
        if (self._balances[asset][self._treasuries[asset]] < redeem_amount or (self._auto_rebalance_threshold > 0 and redeem_amount_wad >= self._auto_rebalance_threshold)) and rebalance_amount_wad < 0:
            withdraw_events = [e for e in tx.raw_events if len(e.topics) > 0 and e.topics[0] == IAssetManagement.Withdraw.selector]
            assert len(withdraw_events) == 1
            _, _, _, _, withdraw_amount_wad, _ = Abi.decode(["uint256", "address", "address", "uint256", "uint256", "uint256"], withdraw_events[0].data)
            #assert withdraw_amount_wad >= -rebalance_amount_wad
            withdraw_amount = withdraw_amount_wad // 10 ** (18 - asset.decimals())
            self._balances[asset][self._treasuries[asset]] += withdraw_amount
            self._treasury_balances[asset] += withdraw_amount_wad

        self._balances[asset][beneficiary] += redeem_amount
        self._balances[asset][self._treasuries[asset]] -= redeem_amount

        self._treasury_balances[asset] -= redeem_amount_wad

        error = abs(expected_redeem_amount_wad - redeem_amount_wad)
        if error > self._max_redeem_error:
            self._max_redeem_error = error
            logger.error(f"Redeem error: expected {expected_redeem_amount_wad} actual {redeem_amount_wad} difference {error / 10 ** 18} {asset.symbol()}")

        self._ip_balances[ip_token][provider] = 0

        logger.info(f"{provider.label} redeemed {amount} {ip_token.symbol()} and received ${redeem_amount} {asset.symbol()}")

    @flow()
    def flow_open_swap(self, tenor: IporTypes.SwapTenor) -> None:
        pay_fixed = random_bool()
        asset = random.choice([self._dai, self._usdc, self._usdt])
        max_leverage = IAmmSwapsLens(self._router).getOpenSwapRiskIndicators(asset, 0 if pay_fixed else 1, tenor).maxLeveragePerLeg
        leverage_wad = random_int(self._min_leverage, max_leverage)
        opener = random_account()
        beneficiary = random_account(predicate=lambda a: a != default_chain.accounts[0])
        total_amount_wad = random_int(1, 10_000) * 10 ** 18 + self._liquidation_deposit + self._publication_fee
        available_amount_wad = total_amount_wad - self._liquidation_deposit - self._publication_fee
        total_amount = total_amount_wad // 10 ** (18 - asset.decimals())

        tenor_length = self._get_tenor_length(tenor)

        collateral_wad = div(available_amount_wad * 10 ** 18, (10 ** 18 + div(leverage_wad * self._opening_fee_rate * tenor_length, (365 * 10 ** 18))))
        opening_fee_wad = available_amount_wad - collateral_wad
        notional_wad = div(collateral_wad * leverage_wad, 10 ** 18)

        offered_rate_pay_fixed, offered_rate_receive_fixed = IAmmSwapsLens(self._router).getOfferedRate(asset, tenor, notional_wad, request_type="call")
        if pay_fixed:
            offered_rate = offered_rate_pay_fixed
            # add a small margin, contract will use current rate which can be slightly different
            acceptable_rate = math.ceil(offered_rate * 1.01)
        else:
            offered_rate = offered_rate_receive_fixed
            # add a small margin, contract will use current rate which can be slightly different
            acceptable_rate = math.floor(offered_rate * 0.99)

        if not pay_fixed and acceptable_rate <= 0:
            return

        mint(asset, opener, total_amount)
        asset.approve(self._router, total_amount, from_=opener)

        open_swap_function = self._open_swap_functions[tenor][asset][pay_fixed]
        with may_revert(("IPOR_302", "IPOR_303", "IPOR_309")) as e:
            tx: TransactionAbc[uint256] = open_swap_function(beneficiary, total_amount, acceptable_rate, leverage_wad, from_=opener)

        # leverage too high or another swap cannot be opened as there is not enough liquidity
        # a swap must be closed first or more liquidity must be provided
        if e.value is not None:
            # burn tokens and revert approval
            asset.transfer(Address(1), total_amount, from_=opener)
            asset.approve(self._router, 0, from_=opener)
            return

        swap_id = tx.return_value
        ibt_quantity = div(notional_wad * 10 ** 18, self._oracle.getAccruedIndex(tx.block.timestamp, asset).ibtPrice)
        self._swaps[asset][swap_id] = Swap(asset, beneficiary, collateral_wad, notional_wad, leverage_wad, 0, ibt_quantity, pay_fixed, tx.block.timestamp, tenor)

        swap = self._swaps[asset][swap_id]
        onchain_swap = next(
            s for s in IAmmSwapsLens(self._router).getSwaps(asset, beneficiary, 0, 50)[1]
            if s.id == swap_id
        )
        assert onchain_swap.collateral == swap.collateral
        assert onchain_swap.notional == swap.notional
        assert onchain_swap.leverage == swap.leverage
        assert onchain_swap.ibtQuantity == swap.ibt_quantity
        assert onchain_swap.openTimestamp == swap.open_timestamp
        self._swaps[asset][swap_id].fixed_rate = onchain_swap.fixedInterestRate  # TODO

        self._balances[asset][self._treasuries[asset]] += total_amount
        opening_fee_treasury = div(opening_fee_wad * self._opening_fee_treasury_portion_rate, 10 ** 18)
        self._ipor_treasury_balances[asset] += opening_fee_treasury
        self._treasury_balances[asset] += opening_fee_wad - opening_fee_treasury

        logger.warning(f"{beneficiary.label} opened swap {swap_id} in {asset.symbol()} with rate {onchain_swap.fixedInterestRate} and notional ${notional_wad}")

        if pay_fixed:
            logger.info(f"{beneficiary.label} opened pay fixed swap {swap_id} in {asset.symbol()} with rate {onchain_swap.fixedInterestRate / 10 ** 16}% and notional ${notional_wad / 10 ** 18}")
        else:
            logger.info(f"{beneficiary.label} opened receive fixed swap {swap_id} in {asset.symbol()} with rate {onchain_swap.fixedInterestRate / 10 ** 16}% and notional ${notional_wad / 10 ** 18}")

    @flow()
    def flow_close_swap(self):
        assets = list(asset for asset, swaps in self._swaps.items() if len(swaps) > 0)
        if len(assets) == 0:
            return

        asset = random.choice(assets)
        swap_id = random.choice(list(self._swaps[asset].keys()))
        self.close_swap(asset, swap_id)

    def close_swap(self, asset: IERC20Metadata, swap_id: uint32) -> None:
        swap = self._swaps[asset][swap_id]
        beneficiary = random_account()

        tenor_length = self._get_tenor_length(swap.tenor)
        buyer_before = self._balances[asset][swap.buyer]
        treasury_before_wad = self._balances[asset][self._treasuries[asset]] * 10 ** (18 - asset.decimals())

        enforce_rebalance = random_bool()
        if enforce_rebalance:
            # enforce rebalance
            deposit_amount_wad = treasury_before_wad - swap.collateral
            deposit_amount = deposit_amount_wad // 10 ** (18 - asset.decimals())
            deposit_amount_wad = deposit_amount * 10 ** (18 - asset.decimals())
            if deposit_amount_wad > 0:
                with may_revert("IPOR_322"):
                    IAmmGovernanceService(self._router).depositToAssetManagement(asset, deposit_amount_wad)

                    self._balances[asset][self._treasuries[asset]] -= deposit_amount
                    self._treasury_balances[asset] -= deposit_amount_wad
                    treasury_before_wad -= deposit_amount_wad

        with default_chain.snapshot_and_revert():
            default_chain.mine()
            offered_rates_block = default_chain.blocks["latest"]
            offered_pay_fixed, offered_receive_fixed = IAmmSwapsLens(self._router).getOfferedRate(asset, swap.tenor, swap.notional, request_type="call")
            vault_before_wad = IAssetManagementLens(self._router).balanceOfAmmTreasuryInAssetManagement(asset)

            if swap.pay_fixed:
                pnl = IAmmSwapsLens(self._router).getPnlPayFixed(asset, swap_id)
            else:
                pnl = IAmmSwapsLens(self._router).getPnlReceiveFixed(asset, swap_id)

        default_chain.set_next_block_timestamp(offered_rates_block.timestamp)
        pending_timestamp = default_chain.blocks["pending"].timestamp

        remaining_time = swap.open_timestamp + tenor_length * 24 * 60 * 60 - pending_timestamp
        min_liquidation_threshold_buyer = div(swap.collateral * self._min_liquidation_threshold_buyer, 10 ** 18)
        min_liquidation_threshold_community = div(swap.collateral * self._min_liquidation_threshold_community, 10 ** 18)

        if 0 < remaining_time <= self._time_before_maturity_community or (abs(pnl) >= min_liquidation_threshold_community and abs(pnl) != swap.collateral):
            closer = random_account(predicate=lambda a: a != default_chain.accounts[0])  # anyone except contract owner
        else:
            closer = swap.buyer

        close_swap_details = IAmmCloseSwapLens(self._router).getClosingSwapDetails(
            asset,
            AmmTypes.SwapDirection.PAY_FIXED_RECEIVE_FLOATING if swap.pay_fixed else AmmTypes.SwapDirection.PAY_FLOATING_RECEIVE_FIXED,
            swap_id,
            pending_timestamp,
            from_=closer,
            request_type="call",
        )

        close_swap_function = self._close_swap_functions[asset]
        tx: TransactionAbc[Tuple[List[AmmTypes.IporSwapClosingResult], List[AmmTypes.IporSwapClosingResult]]] = close_swap_function(
            beneficiary,
            [swap_id] if swap.pay_fixed else [],
            [swap_id] if not swap.pay_fixed else [],
            from_=closer,
        )
        assert tx.block.timestamp == pending_timestamp
        assert tx.block.number == offered_rates_block.number
        assert tx.block.timestamp == offered_rates_block.timestamp

        if remaining_time <= self._time_before_maturity_buyer or abs(pnl) >= min_liquidation_threshold_buyer:
            expected_pnl = self._calculate_pnl_raw(swap, tx.block.number)
            unwinding_fee = 0
        else:
            #unwind
            unwinding_fee = round(swap.notional * self._unwinding_fee_rate / 10 ** 18 * remaining_time / (365 * 24 * 60 * 60))
            if swap.pay_fixed:
                expected_pnl = (
                    self._calculate_pnl_raw(swap, tx.block.number)
                    + round(swap.notional * math.exp(offered_receive_fixed / 10 ** 18 * remaining_time / (365 * 24 * 60 * 60)))
                    - round(swap.notional * math.exp(swap.fixed_rate / 10 ** 18 * remaining_time / (365 * 24 * 60 * 60)))
                    - unwinding_fee
                )
            else:
                expected_pnl = (
                    self._calculate_pnl_raw(swap, tx.block.number)
                    + round(swap.notional * math.exp(swap.fixed_rate / 10 ** 18 * remaining_time / (365 * 24 * 60 * 60)))
                    - round(swap.notional * math.exp(offered_pay_fixed / 10 ** 18 * remaining_time / (365 * 24 * 60 * 60)))
                    - unwinding_fee
                )

            if expected_pnl < -swap.collateral:
                expected_pnl = -swap.collateral
            elif expected_pnl > swap.collateral:
                expected_pnl = swap.collateral

        actual_payoff = asset.balanceOf(swap.buyer) - buyer_before
        actual_payoff_wad = actual_payoff * 10 ** (18 - asset.decimals())

        unwinding_fee_treasury = div(unwinding_fee * self._unwinding_fee_treasury_portion_rate, 10 ** 18)
        self._ipor_treasury_balances[asset] += unwinding_fee_treasury
        self._treasury_balances[asset] -= actual_payoff_wad - swap.collateral + unwinding_fee_treasury

        expected_payoff = swap.collateral + expected_pnl
        if beneficiary == swap.buyer:
            expected_payoff += self._liquidation_deposit
            # actual_payoff_wad contained liquidation deposit which is not part of LP balance
            self._treasury_balances[asset] += self._liquidation_deposit
        else:
            liquidation_deposit = self._liquidation_deposit // 10 ** (18 - asset.decimals())
            self._balances[asset][beneficiary] += liquidation_deposit
            self._balances[asset][self._treasuries[asset]] -= liquidation_deposit

        redeem_amount_wad = swap.collateral + close_swap_details.pnlValue + self._liquidation_deposit
        # rebalance
        if redeem_amount_wad >= treasury_before_wad:
            rebalance_amount_wad = div_int((treasury_before_wad - redeem_amount_wad + vault_before_wad) * (10**18 - self._treasury_asset_management_ratio), 10**18) - vault_before_wad

            if rebalance_amount_wad < 0:
                withdraw_events = [e for e in tx.raw_events if len(e.topics) > 0 and e.topics[0] == IAssetManagement.Withdraw.selector]
                assert len(withdraw_events) == 1
                _, _, _, _, withdraw_amount_wad, _ = Abi.decode(["uint256", "address", "address", "uint256", "uint256", "uint256"], withdraw_events[0].data)
                #assert withdraw_amount_wad >= -rebalance_amount_wad
                withdraw_amount = withdraw_amount_wad // 10 ** (18 - asset.decimals())
                self._balances[asset][self._treasuries[asset]] += withdraw_amount
                self._treasury_balances[asset] += withdraw_amount_wad

        error = abs(expected_payoff - actual_payoff_wad)
        if error > self._max_payoff_error:
            self._max_payoff_error = error
            logger.error(f"Close swap payoff error: expected {expected_payoff} actual {actual_payoff_wad} difference {error / 10 ** 18} {asset.symbol()}")

        self._balances[asset][self._treasuries[asset]] -= actual_payoff
        self._balances[asset][swap.buyer] += actual_payoff

        self._closed_swaps[asset][swap_id] = swap
        del self._swaps[asset][swap_id]

        logger.warning(f"{swap.buyer.label} closed swap {swap_id} in {asset.symbol()} with pnl ${actual_payoff_wad - swap.collateral - self._liquidation_deposit} and payoff ${actual_payoff_wad}")

        logger.info(f"{swap.buyer.label} closed swap {swap_id} in {asset.symbol()} with pnl ${(actual_payoff_wad - swap.collateral - self._liquidation_deposit) / 10 ** 18} and payoff ${actual_payoff_wad / 10 ** 18}")

    @flow()
    def flow_add_appointed_to_rebalance(self):
        asset = random.choice(list(self._appointed_to_rebalance.keys()))
        self._add_appointed_to_rebalance(asset)

    def _add_appointed_to_rebalance(self, asset: IERC20Metadata):
        account = random_account()

        IAmmGovernanceService(self._router).addAppointedToRebalanceInAmm(asset, account)
        self._appointed_to_rebalance[asset].add(account)

    @flow()
    def flow_remove_appointed_to_rebalance(self):
        assets = [asset for asset, accounts in self._appointed_to_rebalance.items() if len(accounts) > 0]
        if len(assets) == 0:
            return
        asset = random.choice(assets)
        account = random.choice(list(self._appointed_to_rebalance[asset]))

        IAmmGovernanceService(self._router).removeAppointedToRebalanceInAmm(asset, account)
        self._appointed_to_rebalance[asset].remove(account)

    @flow()
    def flow_rebalance(self):
        asset = random.choice(list(self._appointed_to_rebalance.keys()))
        if len(self._appointed_to_rebalance[asset]) == len(default_chain.accounts):
            self.flow_remove_appointed_to_rebalance()
        if len(self._appointed_to_rebalance[asset]) == 0:
            self._add_appointed_to_rebalance(asset)
        failing_account = random_account(predicate=lambda a: a not in self._appointed_to_rebalance[asset])
        account = random.choice(list(self._appointed_to_rebalance[asset]))

        with must_revert("IPOR_410"):
            IAmmPoolsService(self._router).rebalanceBetweenAmmTreasuryAndAssetManagement(asset, from_=failing_account)

        treasury_balance_wad = self._balances[asset][self._treasuries[asset]] * 10 ** (18 - asset.decimals())
        with default_chain.snapshot_and_revert():
            default_chain.mine()
            total_balance_block = default_chain.blocks["latest"]
            total_balance_wad = IAssetManagementLens(self._router).balanceOfAmmTreasuryInAssetManagement(asset) + treasury_balance_wad

        ratio = div(treasury_balance_wad * 10 ** 18, total_balance_wad)

        with may_revert(("IPOR_004", "IPOR_504", "IPOR_322")) as e:
            default_chain.set_next_block_timestamp(total_balance_block.timestamp)
            tx = IAmmPoolsService(self._router).rebalanceBetweenAmmTreasuryAndAssetManagement(asset, from_=account)
            assert tx.block.number == total_balance_block.number
            assert tx.block.timestamp == total_balance_block.timestamp

        if e.value == Error("IPOR_322"):
            return

        if ratio > self._treasury_asset_management_ratio:
            rebalance_amount_wad = treasury_balance_wad - div(self._treasury_asset_management_ratio * total_balance_wad, 10 ** 18)
            rebalance_amount = div(rebalance_amount_wad, 10 ** (18 - asset.decimals()))

            if rebalance_amount > 0:
                assert e.value is None
                rebalance_amount_wad = rebalance_amount * 10 ** (18 - asset.decimals())
                self._balances[asset][self._treasuries[asset]] -= rebalance_amount
                self._treasury_balances[asset] -= rebalance_amount_wad
            else:
                assert e.value is not None
        else:
            assert e.value is None or e.value == Error("IPOR_504")

            if e.value is None:
                rebalance_amount_wad = div(self._treasury_asset_management_ratio * total_balance_wad, 10 ** 18) - treasury_balance_wad
                withdraw_events = [e for e in tx.raw_events if len(e.topics) > 0 and e.topics[0] == IAssetManagement.Withdraw.selector]
                assert len(withdraw_events) == 1
                _, _, _, _, withdraw_amount_wad, _ = Abi.decode(["uint256", "address", "address", "uint256", "uint256", "uint256"], withdraw_events[0].data)
                withdraw_amount = withdraw_amount_wad // 10 ** (18 - asset.decimals())
                self._balances[asset][self._treasuries[asset]] += withdraw_amount
                self._treasury_balances[asset] += withdraw_amount_wad

        self.invariant_balances()
        logger.info(f"{account.label} rebalanced {asset.symbol()}")

    @invariant()
    def invariant_payoffs(self):
        closing_block = default_chain.blocks["latest"]

        for asset in self._swaps:
            for swap_id, swap in self._swaps[asset].items():
                expected_payoff_raw = self._calculate_pnl_raw(swap, closing_block.number)

                if swap.pay_fixed:
                    payoff = IAmmSwapsLens(self._router).getPnlPayFixed(asset, swap_id)
                else:
                    payoff = IAmmSwapsLens(self._router).getPnlReceiveFixed(asset, swap_id)

                error = abs(expected_payoff_raw - payoff)
                if error > self._max_payoff_error:
                    self._max_payoff_error = error
                    logger.error(f"Payoff error: expected {expected_payoff_raw} actual {payoff} difference {error / 10 ** 18} {asset.symbol()}")

    @invariant()
    def invariant_lp_balance(self):
        for asset in [self._dai, self._usdc, self._usdt]:
            non_lp_balance = asset.balanceOf(self._treasuries[asset]) * 10 ** (18 - asset.decimals()) - self._treasury_balances[asset]
            expected_non_lp_balance = sum(swap.collateral for swap in self._swaps[asset].values()) + len(self._swaps[asset]) * (self._liquidation_deposit + self._publication_fee) + len(self._closed_swaps[asset]) * self._publication_fee + self._ipor_treasury_balances[asset]
            non_lp_balance_error = abs(non_lp_balance - expected_non_lp_balance)
            if non_lp_balance_error > self._max_non_lp_balance_error:
                self._max_non_lp_balance_error = non_lp_balance_error
                logger.error(f"Non LP balance error: expected {expected_non_lp_balance} actual {non_lp_balance} difference {non_lp_balance_error / 10 ** 18} {asset.symbol()}")

            with default_chain.snapshot_and_revert():
                default_chain.mine()
                t = default_chain.blocks["latest"].number
                claimed_balance = IAmmPoolsLens(self._router).getAmmBalance(asset)

            with default_chain.snapshot_and_revert():
                if claimed_balance.vault > 0:
                    IAmmGovernanceService(self._router).withdrawAllFromAssetManagement(asset)
                    assert default_chain.blocks["latest"].number == t
                actual_balance = IAmmPoolsLens(self._router).getAmmBalance(asset)

            asset_management_error = abs(claimed_balance.liquidityPool - actual_balance.liquidityPool)
            if asset_management_error > self._max_asset_management_error:
                self._max_asset_management_error = asset_management_error
                logger.warning(f"Asset management error: claimed {claimed_balance.liquidityPool} actual {actual_balance.liquidityPool} difference {asset_management_error / 10 ** 18} {asset.symbol()} over time {default_chain.blocks['latest'].timestamp - self.start_timestamp} seconds")

            claimed_treasury_balance = claimed_balance.liquidityPool - claimed_balance.vault
            treasury_error = abs(self._treasury_balances[asset] - claimed_treasury_balance)
            if treasury_error > self._max_treasury_error:
                self._max_treasury_error = treasury_error
                logger.error(f"Treasury error: expected {self._treasury_balances[asset]} actual {claimed_treasury_balance} difference {treasury_error / 10 ** 18} {asset.symbol()}")

            extended_balance = self._storages[asset].getExtendedBalance()
            assert extended_balance.iporPublicationFee == self._publication_fee * (len(self._swaps[asset]) + len(self._closed_swaps[asset]))
            ipor_treasury_error = abs(extended_balance.treasury - self._ipor_treasury_balances[asset])
            if ipor_treasury_error > self._max_ipor_treasury_error:
                self._max_ipor_treasury_error = ipor_treasury_error
                logger.error(f"IPOR treasury error: expected {self._ipor_treasury_balances[asset]} actual {extended_balance.treasury} difference {ipor_treasury_error / 10 ** 18} {asset.symbol()}")

    @invariant()
    def invariant_ip_exchange_rates(self):
        for asset, ip_token in self._ip_tokens.items():
            tx = IAmmPoolsLens(self._router).getIpTokenExchangeRate(asset, request_type="tx")
            expected_exchange_rate = self._calculate_ip_exchange_rate(asset)

            if tx.return_value != expected_exchange_rate:
                rel_error = abs(tx.return_value - expected_exchange_rate) / expected_exchange_rate
                if rel_error > self._max_ip_exchange_rate_error:
                    self._max_ip_exchange_rate_error = rel_error
                    logger.error(f"Ip exchange rate error: expected {expected_exchange_rate} actual {tx.return_value} difference {rel_error * 100}% for {ip_token.symbol()}")

    @invariant()
    def invariant_soap(self):
        for asset in [self._dai, self._usdc, self._usdt]:
            soap_pay_fixed, soap_receive_fixed, _ = IAmmSwapsLens(self._router).getSoap(asset)
            expected_soap_pay_fixed, expected_soap_receive_fixed = self._calculate_soap(asset)

            pay_fixed_error = abs(soap_pay_fixed - expected_soap_pay_fixed)
            receive_fixed_error = abs(soap_receive_fixed - expected_soap_receive_fixed)
            if pay_fixed_error > self._max_soap_error:
                self._max_soap_error = pay_fixed_error
                logger.error(f"SOAP pay fixed error: expected {expected_soap_pay_fixed} actual {soap_pay_fixed} difference {pay_fixed_error / 10 ** 18} {asset.symbol()}")
            if receive_fixed_error > self._max_soap_error:
                self._max_soap_error = receive_fixed_error
                logger.error(f"SOAP receive fixed error: expected {expected_soap_receive_fixed} actual {soap_receive_fixed} difference {receive_fixed_error / 10 ** 18} {asset.symbol()}")

    @invariant()
    def invariant_balances(self):
        for token in self._balances.keys():
            for account, balance in self._balances[token].items():
                assert token.balanceOf(account) == balance

    def print_all_errors(self):
        print(f"Max payoff error: {self._max_payoff_error / 10 ** 18} USD")
        print(f"Max non LP balance error: {self._max_non_lp_balance_error / 10 ** 18} USD")
        print(f"Max asset management error: {self._max_asset_management_error / 10 ** 18} USD")
        print(f"Max treasury error: {self._max_treasury_error / 10 ** 18} USD")
        print(f"Max IPOR treasury error: {self._max_ipor_treasury_error / 10 ** 18} USD")
        print(f"Max IP exchange rate error: {self._max_ip_exchange_rate_error * 100}%")
        print(f"Max SOAP error: {self._max_soap_error / 10 ** 18} USD")
        print(f"Max redeem error: {self._max_redeem_error / 10 ** 18} USD")


def on_revert_handler(e: TransactionRevertedError):
    if e.tx is not None:
        print(e.tx.call_trace)
        print(e.tx.console_logs)


@default_chain.connect(fork=FORK_URL)
@on_revert(on_revert_handler)
def test_ipor_fuzz():
    seed = time.thread_time_ns()
    print(f"Seed: {seed}")
    random.seed(seed)
    for label, account in zip(names, default_chain.accounts):
        account.label = label

    default_chain.set_default_accounts(default_chain.accounts[0])
    IporFuzzTest().run(10, 2_000)
