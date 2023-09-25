from woke.testing import *
from woke.testing.fuzzing import random_address
from pytypes.source.contracts.amm.AmmCloseSwapService import AmmCloseSwapService
from pytypes.source.contracts.amm.AmmGovernanceService import AmmGovernanceService
from pytypes.source.contracts.amm.AmmOpenSwapService import AmmOpenSwapService
from pytypes.source.contracts.amm.AmmPoolsLens import AmmPoolsLens
from pytypes.source.contracts.amm.AmmPoolsService import AmmPoolsService
from pytypes.source.contracts.amm.AmmStorage import AmmStorage
from pytypes.source.contracts.amm.AmmSwapsLens import AmmSwapsLens
from pytypes.source.contracts.amm.AmmTreasury import AmmTreasury
from pytypes.source.contracts.amm.AssetManagementLens import AssetManagementLens
from pytypes.source.contracts.amm.libraries.SoapIndicatorLogic import SoapIndicatorLogic
from pytypes.source.contracts.amm.libraries.SoapIndicatorRebalanceLogic import SoapIndicatorRebalanceLogic
from pytypes.source.contracts.amm.spread.DemandSpreadLibs import DemandSpreadLibs
from pytypes.source.contracts.amm.spread.Spread28Days import Spread28Days
from pytypes.source.contracts.amm.spread.Spread60Days import Spread60Days
from pytypes.source.contracts.amm.spread.Spread90Days import Spread90Days
from pytypes.source.contracts.amm.spread.SpreadCloseSwapService import SpreadCloseSwapService
from pytypes.source.contracts.amm.spread.SpreadRouter import SpreadRouter
from pytypes.source.contracts.amm.spread.SpreadStorageLens import SpreadStorageLens
from pytypes.source.contracts.interfaces.IAmmCloseSwapLens import IAmmCloseSwapLens
from pytypes.source.contracts.interfaces.IAmmGovernanceLens import IAmmGovernanceLens
from pytypes.source.contracts.interfaces.IAmmOpenSwapLens import IAmmOpenSwapLens
from pytypes.source.contracts.interfaces.IAmmPoolsLens import IAmmPoolsLens
from pytypes.source.contracts.interfaces.IAmmPoolsService import IAmmPoolsService
from pytypes.source.contracts.interfaces.IAmmSwapsLens import IAmmSwapsLens
from pytypes.source.contracts.interfaces.IAssetManagementLens import IAssetManagementLens
from pytypes.source.contracts.interfaces.types.IporRiskManagementOracleTypes import IporRiskManagementOracleTypes
from pytypes.source.contracts.oracles.IporOracle import IporOracle
from pytypes.source.contracts.oracles.IporRiskManagementOracle import IporRiskManagementOracle
from pytypes.source.contracts.oracles.OraclePublisher import OraclePublisher
from pytypes.source.contracts.router.IporProtocolRouter import IporProtocolRouter
from pytypes.source.contracts.tokens.IpToken import IpToken
from pytypes.source.contracts.tokens.IporToken import IporToken
from pytypes.source.contracts.tokens.IvToken import IvToken
from pytypes.source.contracts.vault.AssetManagementDai import AssetManagementDai
from pytypes.source.contracts.vault.AssetManagementUsdc import AssetManagementUsdc
from pytypes.source.contracts.vault.AssetManagementUsdt import AssetManagementUsdt
from pytypes.source.contracts.vault.strategies.StrategyAave import StrategyAave
from pytypes.source.contracts.vault.strategies.StrategyCompound import StrategyCompound
from pytypes.source.contracts.vault.interfaces.aave.AaveLendingPoolProviderV2 import AaveLendingPoolProviderV2
from pytypes.source.contracts.vault.interfaces.aave.StakedAaveInterface import StakedAaveInterface
from pytypes.source.contracts.vault.interfaces.aave.AaveIncentivesInterface import AaveIncentivesInterface
from pytypes.source.contracts.vault.interfaces.compound.CErc20 import CErc20
from pytypes.source.contracts.vault.interfaces.compound.Comptroller import Comptroller
from pytypes.openzeppelin.contracts.proxy.ERC1967.ERC1967Proxy import ERC1967Proxy
from pytypes.openzeppelin.contracts.token.ERC20.extensions.IERC20Metadata import IERC20Metadata
from pytypes.tests.Create3Deployer import Create3Deployer
from .utils import deploy_with_proxy


oracle: IporOracle
risk_oracle: IporRiskManagementOracle


def get_oracle() -> IporOracle:
    return oracle


def get_risk_oracle() -> IporRiskManagementOracle:
    return risk_oracle


def get_dai():
    dai = IERC20Metadata("0x6B175474E89094C44Da98b954EedeAC495271d0F")
    assert dai.symbol() == "DAI"
    return dai


def get_usdc():
    usdc = IERC20Metadata("0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48")
    assert usdc.symbol() == "USDC"
    return usdc


def get_usdt():
    usdt = IERC20Metadata("0xdac17f958d2ee523a2206206994597c13d831ec7")
    assert usdt.symbol() == "USDT"
    return usdt


def setup_aave_dai():
    dai = get_dai()

    aave_strategy = deploy_with_proxy(StrategyAave)
    adai = IERC20Metadata("0x028171bCA77440897B824Ca71D1c56caC55b68A3")
    lending_pool_provider = AaveLendingPoolProviderV2("0xB53C1a33016B2DC2fF3653530bfF1848a515c8c5")
    stk_aave = StakedAaveInterface("0x4da27a545c0c5B758a6BA100e3a049001de870f5")
    aave_incentives = AaveIncentivesInterface("0xd784927Ff2f95ba542BfC824c8a8a98F3495f6b5")
    aave_erc20 = IERC20Metadata("0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9")
    aave_strategy.initialize(dai, adai, lending_pool_provider, stk_aave, aave_incentives, aave_erc20)

    return aave_strategy, adai, dai, lending_pool_provider, aave_erc20, stk_aave, aave_incentives


def setup_aave_usdc():
    usdc = get_usdc()

    aave_strategy = deploy_with_proxy(StrategyAave)
    ausdc = IERC20Metadata("0xBcca60bB61934080951369a648Fb03DF4F96263C")
    lending_pool_provider = AaveLendingPoolProviderV2("0xB53C1a33016B2DC2fF3653530bfF1848a515c8c5")
    stk_aave = StakedAaveInterface("0x4da27a545c0c5B758a6BA100e3a049001de870f5")
    aave_incentives = AaveIncentivesInterface("0xd784927Ff2f95ba542BfC824c8a8a98F3495f6b5")
    aave_erc20 = IERC20Metadata("0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9")
    aave_strategy.initialize(usdc, ausdc, lending_pool_provider, stk_aave, aave_incentives, aave_erc20)

    return aave_strategy, ausdc, usdc, lending_pool_provider, aave_erc20, stk_aave, aave_incentives


def setup_aave_usdt():
    usdt = get_usdt()

    aave_strategy = deploy_with_proxy(StrategyAave)
    ausdt = IERC20Metadata("0x3Ed3B47Dd13EC9a98b44e6204A523E766B225811")
    lending_pool_provider = AaveLendingPoolProviderV2("0xB53C1a33016B2DC2fF3653530bfF1848a515c8c5")
    stk_aave = StakedAaveInterface("0x4da27a545c0c5B758a6BA100e3a049001de870f5")
    aave_incentives = AaveIncentivesInterface("0xd784927Ff2f95ba542BfC824c8a8a98F3495f6b5")
    aave_erc20 = IERC20Metadata("0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9")
    aave_strategy.initialize(usdt, ausdt, lending_pool_provider, stk_aave, aave_incentives, aave_erc20)

    return aave_strategy, ausdt, usdt, lending_pool_provider, aave_erc20, stk_aave, aave_incentives


def setup_compound_dai():
    dai = get_dai()

    compound_strategy = deploy_with_proxy(StrategyCompound)
    cdai = CErc20("0x5d3a536e4d6dbd6114cc1ead35777bab948e3643")
    comptroller = Comptroller("0x3d9819210a31b4961b30ef54be2aed79b9c9cd3b")
    comp_erc20 = IERC20Metadata("0xc00e94cb662c3520282e6f5717214004a7f26888")
    compound_strategy.initialize(dai, cdai, comptroller, comp_erc20)

    return compound_strategy, cdai, dai, comp_erc20, comptroller


def setup_compound_usdc():
    usdc = get_usdc()

    compound_strategy = deploy_with_proxy(StrategyCompound)
    cusdc = CErc20("0x39aa39c021dfbae8fac545936693ac917d5e7563")
    comptroller = Comptroller("0x3d9819210a31b4961b30ef54be2aed79b9c9cd3b")
    comp_erc20 = IERC20Metadata("0xc00e94cb662c3520282e6f5717214004a7f26888")
    compound_strategy.initialize(usdc, cusdc, comptroller, comp_erc20)

    return compound_strategy, cusdc, usdc, comp_erc20, comptroller


def setup_compound_usdt():
    usdt = get_usdt()

    compound_strategy = deploy_with_proxy(StrategyCompound)
    cusdt = CErc20("0xf650c3d88d12db855b8bf7d11be6c55a4e07dcc9")
    comptroller = Comptroller("0x3d9819210a31b4961b30ef54be2aed79b9c9cd3b")
    comp_erc20 = IERC20Metadata("0xc00e94cb662c3520282e6f5717214004a7f26888")
    compound_strategy.initialize(usdt, cusdt, comptroller, comp_erc20)

    return compound_strategy, cusdt, usdt, comp_erc20, comptroller


def setup_asset_management_dai():
    dai = get_dai()

    asset_management = deploy_with_proxy(AssetManagementDai)
    ivdai = IvToken.deploy("IvDAI", "IVDAI", dai)
    ivdai.setAssetManagement(asset_management)

    aave_strategy, *_ = setup_aave_dai()
    compound_strategy, *_ = setup_compound_dai()

    aave_strategy.setAssetManagement(asset_management)
    compound_strategy.setAssetManagement(asset_management)

    asset_management.initialize(dai, ivdai, aave_strategy, compound_strategy)
    return asset_management, dai, ivdai, aave_strategy, compound_strategy


def setup_asset_management_usdc():
    usdc = get_usdc()

    asset_management = deploy_with_proxy(AssetManagementUsdc)
    ivusdc = IvToken.deploy("IvUSDC", "IVUSDC", usdc)
    ivusdc.setAssetManagement(asset_management)

    aave_strategy, *_ = setup_aave_usdc()
    compound_strategy, *_ = setup_compound_usdc()

    aave_strategy.setAssetManagement(asset_management)
    compound_strategy.setAssetManagement(asset_management)

    asset_management.initialize(usdc, ivusdc, aave_strategy, compound_strategy)
    return asset_management, usdc, ivusdc, aave_strategy, compound_strategy


def setup_asset_management_usdt():
    usdt = get_usdt()

    asset_management = deploy_with_proxy(AssetManagementUsdt)
    ivusdt = IvToken.deploy("IvUSDT", "IVUSDT", usdt)
    ivusdt.setAssetManagement(asset_management)

    aave_strategy, *_ = setup_aave_usdt()
    compound_strategy, *_ = setup_compound_usdt()

    aave_strategy.setAssetManagement(asset_management)
    compound_strategy.setAssetManagement(asset_management)

    asset_management.initialize(usdt, ivusdt, aave_strategy, compound_strategy)
    return asset_management, usdt, ivusdt, aave_strategy, compound_strategy


def setup_oracles(
    dai, usdc, usdt, *,
    min_pay_fixed_rate = 10,  # in 2 decimals, i.e. 10 = 0.1%
    max_receive_fixed_rate = 1000,  # in 2 decimals, i.e. 1000 = 10%
):
    oracle = IporOracle.deploy(usdt, 1 * 10 ** 18, usdc, 1 * 10 ** 18, dai, 1 * 10 ** 18)  # IBT price should always be initialized to 1, see https://docs.ipor.io/interest-rate-derivatives/ibt
    proxy = ERC1967Proxy.deploy(oracle, b"")
    oracle = IporOracle(proxy)
    timestamp = default_chain.blocks["latest"].timestamp
    oracle.initialize([dai, usdc, usdt], [timestamp] * 3)

    riskmng = deploy_with_proxy(IporRiskManagementOracle)
    riskmng.initialize(
        [dai, usdc, usdt],
        [
            IporRiskManagementOracleTypes.RiskIndicators(
                10000,  # max pay fixed notional in 18 decimals, only used to compute max leverage as max_leverage = max_notional_per_leg / max_collateral_per_leg, 1 = 10k USD
                10000,  # max receive fixed notional in 18 decimals, only used to compute max leverage as max_leverage = max_notional_per_leg / max_collateral_per_leg, 1 = 10k USD
                1000,  # max value of (open swap collateral / liquidity pool collateral) * 10 ** 4 for open swap pay fixed
                1000,  # max value of (open swap collateral / liquidity pool collateral) * 10 ** 4 for open swap receive fixed
                1000,  # max value of (open swap collateral / liquidity pool collateral) * 10 ** 4 for both types
            )  # TODO
        ] * 3,
        [
            IporRiskManagementOracleTypes.BaseSpreadsAndFixedRateCaps(
                100, 150, 200, 300, 350, 480,
                min_pay_fixed_rate, max_receive_fixed_rate,
                min_pay_fixed_rate, max_receive_fixed_rate,
                min_pay_fixed_rate, max_receive_fixed_rate,
            )  # TODO
        ] * 3,
    )

    publisher = OraclePublisher.deploy(oracle,riskmng)
    proxy = ERC1967Proxy.deploy(publisher, b"")
    publisher = OraclePublisher(proxy)
    publisher.initialize()

    return oracle, riskmng, publisher


def setup_router(
    liquidation_deposit = 25,  # amount of USD taken on swap open and returned on swap close (unless liquidated)
    max_swap_collateral = 100_000 * 10 ** 18,  # max amount of collateral when opening swap in 18 decimals, i.e. 100_000 * 10 ** 18 = 100_000
    publication_fee = 10 * 10 ** 18,  # amount of USD taken on swap open as a fee (as a compensation for oracle updates)
    opening_fee_rate = 10 ** 16,  # fee in 18 decimals, i.e. 10 ** 18 = 100%
    opening_fee_treasury_portion_rate = 0,  # portion of the opening fee that goes to the treasury (the rest goes to a liquidity pool), in 18 decimals, i.e. 10 ** 18 = 100%
    min_leverage = 10 * 10 ** 18,  # minimum leverage for open swap in 18 decimals, where leverage = collateral / notional
    time_before_maturity_community = 1 * 60 * 60,  # time before maturity in seconds, after which the community can close the swap
    time_before_maturiy_buyer = 24 * 60 * 60,  # time before maturity in seconds, after which the buyer can close the swap
    min_liquidation_threshold_community = 995 * 10 ** 15,  # minimum threshold for liquidation by community in 18 decimals, i.e. 995 * 10 ** 15 = 99.5%
    min_liquidation_threshold_buyer = 990 * 10 ** 15,  # minimum threshold for liquidation by buyer in 18 decimals, i.e. 990 * 10 ** 15 = 99%
    unwinding_fee_rate = 10 ** 16,  # fee applied on swap unwinding amount in 18 decimals, i.e. 10 ** 18 = 100%
    unwinding_fee_treasury_portion_rate = 0,  # portion of the unwinding fee that goes to the treasury (the rest goes to a liquidity pool), in 18 decimals, i.e. 10 ** 18 = 100%
    redeem_fee_rate = 5 * 10 ** 15,  # redeem fee applied on ip_redeem_amount * ip_exchange_rate, in 18 decimals, i.e. 5 * 10 ** 15 = 0.5%
    redeem_lp_max_collateral_ratio = 1 * 10 ** 18,  # max total_collateral_for_both_legs / (lp_balance - redeem_balance) ratio allowed when redeeming from LP, in 18 decimals, i.e. 10 ** 18 = 100%
):
    global oracle, risk_oracle

    a = default_chain.accounts[0]

    # deploy libraries
    SoapIndicatorLogic.deploy()
    SoapIndicatorRebalanceLogic.deploy()
    DemandSpreadLibs.deploy()

    # fork tokens
    dai = get_dai()
    usdc = get_usdc()
    usdt = get_usdt()

    # deploy IPOR token
    ipor_token = IporToken.deploy("IPOR", "IPOR", a)

    # deploy ip tokens
    iptoken_dai = IpToken.deploy("ipDAI", "ipDAI", dai)
    iptoken_usdc = IpToken.deploy("ipUSDC", "ipUSDC", usdc)
    iptoken_usdt = IpToken.deploy("ipUSDT", "ipUSDT", usdt)

    # deploy asset managment
    assetmngmt_dai, *_ = setup_asset_management_dai()
    assetmngmt_usdc, *_ = setup_asset_management_usdc()
    assetmngmt_usdt, *_ = setup_asset_management_usdt()

    # deploy oracle components
    oracle, risk_oracle, publisher = setup_oracles(dai, usdc, usdt)

    '''
        Precompute addresses for AMM deployment
    '''

    create3deployer = Create3Deployer.deploy()

    # get router address
    router = IporProtocolRouter(create3deployer.getAddress(b"router"))

    '''
        Configure Ip tokens
    '''

    for iptoken in [iptoken_dai, iptoken_usdc, iptoken_usdt]:
        iptoken.setJoseph(router)

    '''
        Deploy AMM contracts
    '''

    # AMM storage & treasury must be deployed per asset
    amm_storages = []
    amm_treasuries = []
    for asset, assetmngmt in zip([dai, usdc, usdt], [assetmngmt_dai, assetmngmt_usdc, assetmngmt_usdt]):
        ammtreasury = AmmTreasury(create3deployer.getAddress(asset.symbol().encode() + b"ammtreasury"))

        # deploy AMM storage
        ammstorage_impl = AmmStorage.deploy(router, ammtreasury)
        proxy = ERC1967Proxy.deploy(ammstorage_impl, b"")
        ammstorage = AmmStorage(proxy)
        ammstorage.initialize()

        # deploy AMM treasury
        ammtreasury_impl = AmmTreasury.deploy(asset, asset.decimals(), ammstorage, assetmngmt, router)
        assert create3deployer.deploy_(
            asset.symbol().encode() + b"ammtreasury",
            ERC1967Proxy.get_creation_code() + Abi.encode(["address", "bytes"], [ammtreasury_impl, b""])
        ).return_value == ammtreasury.address
        ammtreasury.initialize(False)
        ammtreasury.grandMaxAllowanceForSpender(router)
        ammtreasury.grandMaxAllowanceForSpender(assetmngmt)

        amm_storages.append(ammstorage)
        amm_treasuries.append(ammtreasury)

    ammstorage_dai, ammstorage_usdc, ammstorage_usdt = amm_storages
    ammtreasury_dai, ammtreasury_usdc, ammtreasury_usdt = amm_treasuries

    assetmngmt_dai.setAmmTreasury(ammtreasury_dai)
    assetmngmt_usdc.setAmmTreasury(ammtreasury_usdc)
    assetmngmt_usdt.setAmmTreasury(ammtreasury_usdt)

    # deploy spread router
    spread28 = Spread28Days.deploy(dai, usdc, usdt)
    spread60 = Spread60Days.deploy(dai, usdc, usdt)
    spread90 = Spread90Days.deploy(dai, usdc, usdt)
    spreadlens = SpreadStorageLens.deploy()
    spread_csservice = SpreadCloseSwapService.deploy(dai, usdc, usdt)
    spreadrouter = SpreadRouter.deploy(
        SpreadRouter.DeployedContracts(router.address, spread28.address, spread60.address, spread90.address, spreadlens.address, spread_csservice.address)
    )

    # deploy AMM lens & services
    swaplens = AmmSwapsLens.deploy(
        IAmmSwapsLens.SwapLensPoolConfiguration(usdt.address, ammstorage_usdt.address, ammtreasury_usdt.address, min_leverage),
        IAmmSwapsLens.SwapLensPoolConfiguration(usdc.address, ammstorage_usdc.address, ammtreasury_usdc.address, min_leverage),
        IAmmSwapsLens.SwapLensPoolConfiguration(dai.address, ammstorage_dai.address, ammtreasury_dai.address, min_leverage),
        oracle,
        risk_oracle,
        spreadrouter,
    )
    poollens = AmmPoolsLens.deploy(
        IAmmPoolsLens.AmmPoolsLensPoolConfiguration(usdt.address, 6, iptoken_usdt.address, ammstorage_usdt.address, ammtreasury_usdt.address, assetmngmt_usdt.address),
        IAmmPoolsLens.AmmPoolsLensPoolConfiguration(usdc.address, 6, iptoken_usdc.address, ammstorage_usdc.address, ammtreasury_usdc.address, assetmngmt_usdc.address),
        IAmmPoolsLens.AmmPoolsLensPoolConfiguration(dai.address, 18, iptoken_dai.address, ammstorage_dai.address, ammtreasury_dai.address, assetmngmt_dai.address),
        oracle
    )
    amlens = AssetManagementLens.deploy(
        IAssetManagementLens.AssetManagementConfiguration(usdt.address, 6, assetmngmt_usdt.address, ammtreasury_usdt.address),
        IAssetManagementLens.AssetManagementConfiguration(usdc.address, 6, assetmngmt_usdc.address, ammtreasury_usdc.address),
        IAssetManagementLens.AssetManagementConfiguration(dai.address, 18, assetmngmt_dai.address, ammtreasury_dai.address)
    )
    osservice = AmmOpenSwapService.deploy(
        IAmmOpenSwapLens.AmmOpenSwapServicePoolConfiguration(usdt.address, 6, ammstorage_usdt.address, ammtreasury_usdt.address, publication_fee, max_swap_collateral, liquidation_deposit, min_leverage, opening_fee_rate, opening_fee_treasury_portion_rate),
        IAmmOpenSwapLens.AmmOpenSwapServicePoolConfiguration(usdc.address, 6, ammstorage_usdc.address, ammtreasury_usdc.address, publication_fee, max_swap_collateral, liquidation_deposit, min_leverage, opening_fee_rate, opening_fee_treasury_portion_rate),
        IAmmOpenSwapLens.AmmOpenSwapServicePoolConfiguration(dai.address, 18, ammstorage_dai.address, ammtreasury_dai.address, publication_fee, max_swap_collateral, liquidation_deposit, min_leverage, opening_fee_rate, opening_fee_treasury_portion_rate),
        oracle,
        risk_oracle,
        spreadrouter
    )
    csservice = AmmCloseSwapService.deploy(
        IAmmCloseSwapLens.AmmCloseSwapServicePoolConfiguration(usdt.address, 6, ammstorage_usdt.address, ammtreasury_usdt.address, assetmngmt_usdt.address, unwinding_fee_rate, unwinding_fee_treasury_portion_rate, 100, time_before_maturity_community, time_before_maturiy_buyer, min_liquidation_threshold_community, min_liquidation_threshold_buyer, min_leverage),
        IAmmCloseSwapLens.AmmCloseSwapServicePoolConfiguration(usdc.address, 6, ammstorage_usdc.address, ammtreasury_usdc.address, assetmngmt_usdc.address, unwinding_fee_rate, unwinding_fee_treasury_portion_rate, 100, time_before_maturity_community, time_before_maturiy_buyer, min_liquidation_threshold_community, min_liquidation_threshold_buyer, min_leverage),
        IAmmCloseSwapLens.AmmCloseSwapServicePoolConfiguration(dai.address, 18, ammstorage_dai.address, ammtreasury_dai.address, assetmngmt_dai.address, unwinding_fee_rate, unwinding_fee_treasury_portion_rate, 100, time_before_maturity_community, time_before_maturiy_buyer, min_liquidation_threshold_community, min_liquidation_threshold_buyer, min_leverage),
        oracle,
        risk_oracle,
        spreadrouter
    )
    pservice = AmmPoolsService.deploy(
        IAmmPoolsService.AmmPoolsServicePoolConfiguration(usdt.address, 6, iptoken_usdt.address, ammstorage_usdt.address, ammtreasury_usdt.address, assetmngmt_usdt.address, redeem_fee_rate, redeem_lp_max_collateral_ratio),
        IAmmPoolsService.AmmPoolsServicePoolConfiguration(usdc.address, 6, iptoken_usdc.address, ammstorage_usdc.address, ammtreasury_usdc.address, assetmngmt_usdc.address, redeem_fee_rate, redeem_lp_max_collateral_ratio),
        IAmmPoolsService.AmmPoolsServicePoolConfiguration(dai.address, 18, iptoken_dai.address, ammstorage_dai.address, ammtreasury_dai.address, assetmngmt_dai.address, redeem_fee_rate, redeem_lp_max_collateral_ratio),
        oracle
    )
    gservice = AmmGovernanceService.deploy(
        IAmmGovernanceLens.AmmGovernancePoolConfiguration(usdt.address, 6, ammstorage_usdt.address, ammtreasury_usdt.address, a.address, a.address, a.address, a.address),
        IAmmGovernanceLens.AmmGovernancePoolConfiguration(usdc.address, 6, ammstorage_usdc.address, ammtreasury_usdc.address, a.address, a.address, a.address, a.address),
        IAmmGovernanceLens.AmmGovernancePoolConfiguration(dai.address, 18, ammstorage_dai.address, ammtreasury_dai.address, a.address, a.address, a.address, a.address)
    )

    # IMPORTANT: liquidity mining contracts are not deployed & configured here
    dummy_addr = random_address()

    # finally deploy the routerrrrr
    router_impl = IporProtocolRouter.deploy(
        IporProtocolRouter.DeployedContracts(
            swaplens.address, poollens.address, amlens.address, osservice.address, csservice.address,
            pservice.address, gservice.address, dummy_addr, dummy_addr, dummy_addr, dummy_addr,
        ),
    )
    assert create3deployer.deploy_(
        b"router",
        ERC1967Proxy.get_creation_code() + Abi.encode(["address", "bytes"], [router_impl, b""])
    ).return_value == router.address
    router.initialize(False)

    return router
