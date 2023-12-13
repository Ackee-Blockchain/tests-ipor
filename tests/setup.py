from wake.testing import *
from wake.testing.fuzzing import random_address
from pytypes.source.contracts.amm.AmmCloseSwapServiceDai import AmmCloseSwapServiceDai
from pytypes.source.contracts.amm.AmmCloseSwapServiceUsdc import AmmCloseSwapServiceUsdc
from pytypes.source.contracts.amm.AmmCloseSwapServiceUsdt import AmmCloseSwapServiceUsdt
from pytypes.source.contracts.amm.AmmOpenSwapService import AmmOpenSwapService
from pytypes.source.contracts.amm.AmmPoolsLens import AmmPoolsLens
from pytypes.source.contracts.amm.AmmPoolsService import AmmPoolsService
from pytypes.source.contracts.amm.AmmStorage import AmmStorage
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
from pytypes.source.contracts.amm.spread.SpreadStorageService import SpreadStorageService
from pytypes.source.contracts.ammcommon.AmmCloseSwapLens import AmmCloseSwapLens
from pytypes.source.contracts.ammcommon.AmmGovernanceService import AmmGovernanceService
from pytypes.source.contracts.ammcommon.AmmSwapsLens import AmmSwapsLens
from pytypes.source.contracts.ammeth.AmmCloseSwapServiceStEth import AmmCloseSwapServiceStEth
from pytypes.source.contracts.ammeth.AmmOpenSwapServiceStEth import AmmOpenSwapServiceStEth
from pytypes.source.contracts.ammeth.AmmPoolsLensStEth import AmmPoolsLensStEth
from pytypes.source.contracts.ammeth.AmmPoolsServiceStEth import AmmPoolsServiceStEth
from pytypes.source.contracts.base.amm.AmmStorageBaseV1 import AmmStorageBaseV1
from pytypes.source.contracts.base.amm.AmmTreasuryBaseV1 import AmmTreasuryBaseV1
from pytypes.source.contracts.base.amm.libraries.AmmSwapsLensLibBaseV1 import AmmSwapsLensLibBaseV1
from pytypes.source.contracts.base.spread.SpreadBaseV1 import SpreadBaseV1
from pytypes.source.contracts.base.types.AmmTypesBaseV1 import AmmTypesBaseV1
from pytypes.source.contracts.interfaces.IAmmCloseSwapLens import IAmmCloseSwapLens
from pytypes.source.contracts.interfaces.IAmmGovernanceLens import IAmmGovernanceLens
from pytypes.source.contracts.interfaces.IAmmOpenSwapLens import IAmmOpenSwapLens
from pytypes.source.contracts.interfaces.IAmmPoolsLens import IAmmPoolsLens
from pytypes.source.contracts.interfaces.IAmmPoolsService import IAmmPoolsService
from pytypes.source.contracts.interfaces.IAmmSwapsLens import IAmmSwapsLens
from pytypes.source.contracts.interfaces.IAssetManagementLens import IAssetManagementLens
from pytypes.source.contracts.oracles.IporOracle import IporOracle
from pytypes.source.contracts.router.IporProtocolRouter import IporProtocolRouter
from pytypes.source.contracts.tokens.IpToken import IpToken
from pytypes.source.contracts.tokens.IporToken import IporToken
from pytypes.source.contracts.vault.AssetManagementDai import AssetManagementDai
from pytypes.source.contracts.vault.AssetManagementUsdc import AssetManagementUsdc
from pytypes.source.contracts.vault.AssetManagementUsdt import AssetManagementUsdt
from pytypes.source.contracts.vault.strategies.StrategyAave import StrategyAave
from pytypes.source.contracts.vault.strategies.StrategyCompound import StrategyCompound
from pytypes.source.contracts.vault.strategies.StrategyDsrDai import StrategyDsrDai
from pytypes.source.contracts.vault.interfaces.aave.AaveLendingPoolProviderV2 import AaveLendingPoolProviderV2
from pytypes.source.contracts.vault.interfaces.aave.StakedAaveInterface import StakedAaveInterface
from pytypes.source.contracts.vault.interfaces.aave.AaveIncentivesInterface import AaveIncentivesInterface
from pytypes.source.contracts.vault.interfaces.compound.CErc20 import CErc20
from pytypes.source.contracts.vault.interfaces.compound.Comptroller import Comptroller
from pytypes.openzeppelin.contracts.proxy.ERC1967.ERC1967Proxy import ERC1967Proxy
from pytypes.openzeppelin.contracts.token.ERC20.extensions.IERC20Metadata import IERC20Metadata
from pytypes.tests.Create3Deployer import Create3Deployer


oracle: IporOracle


def get_oracle() -> IporOracle:
    return oracle


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


def get_steth():
    st_eth = IERC20Metadata("0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84")
    assert st_eth.symbol() == "stETH"
    return st_eth


def get_weth():
    weth = IERC20Metadata("0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2")
    assert weth.symbol() == "WETH"
    return weth


def get_wsteth():
    wst_eth = IERC20Metadata("0x7f39C581F595B53c5cb19bD0b3f8dA6c935E2Ca0")
    assert wst_eth.symbol() == "wstETH"
    return wst_eth


def setup_aave_dai(create3: Create3Deployer):
    dai = get_dai()

    adai = IERC20Metadata("0x028171bCA77440897B824Ca71D1c56caC55b68A3")
    lending_pool_provider = AaveLendingPoolProviderV2("0xB53C1a33016B2DC2fF3653530bfF1848a515c8c5")
    stk_aave = StakedAaveInterface("0x4da27a545c0c5B758a6BA100e3a049001de870f5")
    aave_incentives = AaveIncentivesInterface("0xd784927Ff2f95ba542BfC824c8a8a98F3495f6b5")
    aave_erc20 = IERC20Metadata("0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9")

    aave_strategy = StrategyAave.deploy(
        dai, 18, adai, create3.getAddress(b"dai_asset_management"),
        aave_erc20, stk_aave, lending_pool_provider, aave_incentives
    )
    aave_strategy = ERC1967Proxy.deploy(
        aave_strategy,
        Abi.encode_call(StrategyAave.initialize, [])
    )

    return aave_strategy, adai, dai, lending_pool_provider, aave_erc20, stk_aave, aave_incentives


def setup_aave_usdc(create3: Create3Deployer):
    usdc = get_usdc()

    ausdc = IERC20Metadata("0xBcca60bB61934080951369a648Fb03DF4F96263C")
    lending_pool_provider = AaveLendingPoolProviderV2("0xB53C1a33016B2DC2fF3653530bfF1848a515c8c5")
    stk_aave = StakedAaveInterface("0x4da27a545c0c5B758a6BA100e3a049001de870f5")
    aave_incentives = AaveIncentivesInterface("0xd784927Ff2f95ba542BfC824c8a8a98F3495f6b5")
    aave_erc20 = IERC20Metadata("0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9")

    aave_strategy = StrategyAave.deploy(
        usdc, 6, ausdc, create3.getAddress(b"usdc_asset_management"),
        aave_erc20, stk_aave, lending_pool_provider, aave_incentives,
    )
    aave_strategy = ERC1967Proxy.deploy(
        aave_strategy,
        Abi.encode_call(StrategyAave.initialize, [])
    )

    return aave_strategy, ausdc, usdc, lending_pool_provider, aave_erc20, stk_aave, aave_incentives


def setup_aave_usdt(create3: Create3Deployer):
    usdt = get_usdt()

    ausdt = IERC20Metadata("0x3Ed3B47Dd13EC9a98b44e6204A523E766B225811")
    lending_pool_provider = AaveLendingPoolProviderV2("0xB53C1a33016B2DC2fF3653530bfF1848a515c8c5")
    stk_aave = StakedAaveInterface("0x4da27a545c0c5B758a6BA100e3a049001de870f5")
    aave_incentives = AaveIncentivesInterface("0xd784927Ff2f95ba542BfC824c8a8a98F3495f6b5")
    aave_erc20 = IERC20Metadata("0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9")

    aave_strategy = StrategyAave.deploy(
        usdt, 6, ausdt, create3.getAddress(b"usdt_asset_management"),
        aave_erc20, stk_aave, lending_pool_provider, aave_incentives,
    )
    aave_strategy = ERC1967Proxy.deploy(
        aave_strategy,
        Abi.encode_call(StrategyAave.initialize, [])
    )

    return aave_strategy, ausdt, usdt, lending_pool_provider, aave_erc20, stk_aave, aave_incentives


def setup_compound_dai(create3: Create3Deployer):
    dai = get_dai()

    cdai = CErc20("0x5d3a536e4d6dbd6114cc1ead35777bab948e3643")
    comptroller = Comptroller("0x3d9819210a31b4961b30ef54be2aed79b9c9cd3b")
    comp_erc20 = IERC20Metadata("0xc00e94cb662c3520282e6f5717214004a7f26888")

    compound_strategy = StrategyCompound.deploy(
        dai, dai.decimals(), cdai, create3.getAddress(b"dai_asset_management"),
        7100, comptroller, comp_erc20,
    )
    compound_strategy = ERC1967Proxy.deploy(
        compound_strategy,
        Abi.encode_call(StrategyCompound.initialize, [])
    )

    return compound_strategy, cdai, dai, comp_erc20, comptroller


def setup_compound_usdc(create3: Create3Deployer):
    usdc = get_usdc()

    cusdc = CErc20("0x39aa39c021dfbae8fac545936693ac917d5e7563")
    comptroller = Comptroller("0x3d9819210a31b4961b30ef54be2aed79b9c9cd3b")
    comp_erc20 = IERC20Metadata("0xc00e94cb662c3520282e6f5717214004a7f26888")

    compound_strategy = StrategyCompound.deploy(
        usdc, usdc.decimals(), cusdc, create3.getAddress(b"usdc_asset_management"),
        7100, comptroller, comp_erc20,
    )
    compound_strategy = ERC1967Proxy.deploy(
        compound_strategy,
        Abi.encode_call(StrategyCompound.initialize, [])
    )

    return compound_strategy, cusdc, usdc, comp_erc20, comptroller


def setup_compound_usdt(create3: Create3Deployer):
    usdt = get_usdt()

    cusdt = CErc20("0xf650c3d88d12db855b8bf7d11be6c55a4e07dcc9")
    comptroller = Comptroller("0x3d9819210a31b4961b30ef54be2aed79b9c9cd3b")
    comp_erc20 = IERC20Metadata("0xc00e94cb662c3520282e6f5717214004a7f26888")

    compound_strategy = StrategyCompound.deploy(
        usdt, usdt.decimals(), cusdt, create3.getAddress(b"usdt_asset_management"),
        7100, comptroller, comp_erc20,
    )
    compound_strategy = ERC1967Proxy.deploy(
        compound_strategy,
        Abi.encode_call(StrategyCompound.initialize, [])
    )

    return compound_strategy, cusdt, usdt, comp_erc20, comptroller


def setup_dsr_dai(create3: Create3Deployer):
    dai = get_dai()

    sdai = IERC20Metadata("0x83F20F44975D03b1b09e64809B757c47f942BEeA")

    dsr_strategy = StrategyDsrDai.deploy(
        dai, sdai, create3.getAddress(b"dai_asset_management"),
    )
    dsr_strategy = ERC1967Proxy.deploy(
        dsr_strategy,
        Abi.encode_call(StrategyDsrDai.initialize, [])
    )

    return dsr_strategy, sdai, dai


def setup_asset_management_dai(create3: Create3Deployer):
    dai = get_dai()

    aave_strategy, *_ = setup_aave_dai(create3)
    compound_strategy, *_ = setup_compound_dai(create3)
    dsr_strategy, *_ = setup_dsr_dai(create3)

    asset_management = AssetManagementDai.deploy(
        dai,
        create3.getAddress(dai.symbol().encode() + b"ammtreasury"),
        aave_strategy,
        compound_strategy,
        dsr_strategy,
    )
    asset_management = AssetManagementDai(create3.deploy_(
        b"dai_asset_management",
        ERC1967Proxy.get_creation_code() + Abi.encode(
            ["address", "bytes"],
            [asset_management, b""],
        )
    ).return_value)
    asset_management.initialize()
    for strategy in [aave_strategy, compound_strategy, dsr_strategy]:
        asset_management.grantMaxAllowanceForSpender(dai, strategy)

    return asset_management, dai, aave_strategy, compound_strategy, dsr_strategy


def setup_asset_management_usdc(create3: Create3Deployer):
    usdc = get_usdc()

    aave_strategy, *_ = setup_aave_usdc(create3)
    compound_strategy, *_ = setup_compound_usdc(create3)

    asset_management = AssetManagementUsdc.deploy(
        usdc,
        create3.getAddress(usdc.symbol().encode() + b"ammtreasury"),
        aave_strategy,
        compound_strategy,
    )
    asset_management = AssetManagementUsdc(create3.deploy_(
        b"usdc_asset_management",
        ERC1967Proxy.get_creation_code() + Abi.encode(
            ["address", "bytes"],
            [asset_management, b""],
        )
    ).return_value)
    asset_management.initialize()
    for strategy in [aave_strategy, compound_strategy]:
        asset_management.grantMaxAllowanceForSpender(usdc, strategy)

    return asset_management, usdc, aave_strategy, compound_strategy


def setup_asset_management_usdt(create3: Create3Deployer):
    usdt = get_usdt()

    aave_strategy, *_ = setup_aave_usdt(create3)
    compound_strategy, *_ = setup_compound_usdt(create3)

    asset_management = AssetManagementUsdt.deploy(
        usdt,
        create3.getAddress(usdt.symbol().encode() + b"ammtreasury"),
        aave_strategy,
        compound_strategy,
    )
    asset_management = AssetManagementUsdt(create3.deploy_(
        b"usdt_asset_management",
        ERC1967Proxy.get_creation_code() + Abi.encode(
            ["address", "bytes"],
            [asset_management, b""],
        )
    ).return_value)
    asset_management.initialize()
    for strategy in [aave_strategy, compound_strategy]:
        asset_management.grantMaxAllowanceForSpender(usdt, strategy)

    return asset_management, usdt, aave_strategy, compound_strategy


def setup_oracle(
    dai, usdc, usdt, st_eth,
):
    oracle = IporOracle.deploy(usdt, 1 * 10 ** 18, usdc, 1 * 10 ** 18, dai, 1 * 10 ** 18, st_eth)  # IBT price should always be initialized to 1, see https://docs.ipor.io/interest-rate-derivatives/ibt
    proxy = ERC1967Proxy.deploy(oracle, b"")
    oracle = IporOracle(proxy)
    timestamp = default_chain.blocks["latest"].timestamp
    oracle.initialize([dai, usdc, usdt], [timestamp] * 3)

    return oracle


def setup_router(
    message_signer: Account,
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
    time_after_open_wihout_unwinding = 1 * 24 * 60 * 60,  # time after open swap when unwinding won't be applied, in seconds
):
    global oracle, risk_oracle

    a = default_chain.accounts[0]

    # deploy libraries
    SoapIndicatorLogic.deploy()
    SoapIndicatorRebalanceLogic.deploy()
    DemandSpreadLibs.deploy()
    AmmSwapsLensLibBaseV1.deploy()

    create3deployer = Create3Deployer.deploy()

    # fork tokens
    dai = get_dai()
    usdc = get_usdc()
    usdt = get_usdt()
    st_eth = get_steth()
    weth = get_weth()
    ipst_eth = IpToken.deploy("ipstETH", "ipstETH", st_eth)

    # deploy IPOR token
    ipor_token = IporToken.deploy("IPOR", "IPOR", a)

    # deploy ip tokens
    iptoken_dai = IpToken.deploy("ipDAI", "ipDAI", dai)
    iptoken_usdc = IpToken.deploy("ipUSDC", "ipUSDC", usdc)
    iptoken_usdt = IpToken.deploy("ipUSDT", "ipUSDT", usdt)

    # deploy asset managment
    assetmngmt_dai, *_ = setup_asset_management_dai(create3deployer)
    assetmngmt_usdc, *_ = setup_asset_management_usdc(create3deployer)
    assetmngmt_usdt, *_ = setup_asset_management_usdt(create3deployer)

    # deploy oracle components
    oracle = setup_oracle(dai, usdc, usdt, st_eth)

    # get router address
    router = IporProtocolRouter(create3deployer.getAddress(b"router"))

    '''
        Configure Ip tokens
    '''

    for iptoken in [iptoken_dai, iptoken_usdc, iptoken_usdt, ipst_eth]:
        iptoken.setTokenManager(router)

    '''
        Deploy AMM contracts
    '''

    # AMM storage & treasury must be deployed per asset
    amm_storages: List[AmmStorage] = []
    amm_treasuries: List[AmmTreasury] = []
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
        ammtreasury.grantMaxAllowanceForSpender(router)
        ammtreasury.grantMaxAllowanceForSpender(assetmngmt)

        amm_storages.append(ammstorage)
        amm_treasuries.append(ammtreasury)

    ammstorage_dai, ammstorage_usdc, ammstorage_usdt = amm_storages
    ammtreasury_dai, ammtreasury_usdc, ammtreasury_usdt = amm_treasuries

    # prepare stETH treaury address
    ammtreasury_st_eth = AmmTreasuryBaseV1(create3deployer.getAddress(st_eth.symbol().encode() + b"ammtreasury"))

    # deploy stETH AMM storage
    ammstorage_st_eth = AmmStorageBaseV1.deploy(router)
    ammstorage_st_eth = ERC1967Proxy.deploy(
        ammstorage_st_eth,
        Abi.encode_call(AmmStorage.initialize, [])
    )

    # deploy stETH AMM treasury
    ammtreasury_st_eth_impl = AmmTreasuryBaseV1.deploy(st_eth, router, ammstorage_st_eth)
    assert create3deployer.deploy_(
        st_eth.symbol().encode() + b"ammtreasury",
        ERC1967Proxy.get_creation_code() + Abi.encode(
            ["address", "bytes"],
            [ammtreasury_st_eth_impl, b""]
        )
    ).return_value == ammtreasury_st_eth.address
    ammtreasury_st_eth.initialize(False)

    # deploy spread router
    spread28 = Spread28Days.deploy(dai, usdc, usdt)
    spread60 = Spread60Days.deploy(dai, usdc, usdt)
    spread90 = Spread90Days.deploy(dai, usdc, usdt)
    spread_storage_lens = SpreadStorageLens.deploy()
    spread_csservice = SpreadCloseSwapService.deploy(dai, usdc, usdt)
    spread_storage_service = SpreadStorageService.deploy()
    spreadrouter = SpreadRouter.deploy(
        SpreadRouter.DeployedContracts(
            router.address, spread28.address, spread60.address, spread90.address,
            spread_storage_lens.address, spread_csservice.address, spread_storage_service.address,
        )
    )

    steth_spread = SpreadBaseV1.deploy(router, st_eth, [])

    # deploy AMM lens & services
    swaplens = AmmSwapsLens.deploy(
        IAmmSwapsLens.SwapLensPoolConfiguration(usdt.address, ammstorage_usdt.address, ammtreasury_usdt.address, spreadrouter.address),
        IAmmSwapsLens.SwapLensPoolConfiguration(usdc.address, ammstorage_usdc.address, ammtreasury_usdc.address, spreadrouter.address),
        IAmmSwapsLens.SwapLensPoolConfiguration(dai.address, ammstorage_dai.address, ammtreasury_dai.address, spreadrouter.address),
        IAmmSwapsLens.SwapLensPoolConfiguration(st_eth.address, ammstorage_st_eth.address, ammtreasury_st_eth.address, steth_spread.address),
        oracle,
        message_signer,
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
        message_signer,
        spreadrouter
    )
    osservice_st_eth = AmmOpenSwapServiceStEth.deploy(
        AmmTypesBaseV1.AmmOpenSwapServicePoolConfiguration(
            st_eth.address, st_eth.decimals(), ammstorage_st_eth.address, ammtreasury_st_eth.address, steth_spread.address,
            publication_fee, max_swap_collateral, liquidation_deposit, min_leverage, opening_fee_rate, opening_fee_treasury_portion_rate,
        ),
        oracle,
        message_signer,
        weth,
        get_wsteth(),
    )
    css_service_dai = AmmCloseSwapServiceDai.deploy(
        IAmmCloseSwapLens.AmmCloseSwapServicePoolConfiguration(
            dai.address, dai.decimals(), ammstorage_dai.address, ammtreasury_dai.address, assetmngmt_dai.address,
            spreadrouter.address, unwinding_fee_rate, unwinding_fee_treasury_portion_rate, 100,
            time_before_maturity_community, time_before_maturiy_buyer, min_liquidation_threshold_community,
            min_liquidation_threshold_buyer, min_leverage, time_after_open_wihout_unwinding,
        ),
        oracle,
        message_signer,
    )
    css_service_usdc = AmmCloseSwapServiceUsdc.deploy(
        IAmmCloseSwapLens.AmmCloseSwapServicePoolConfiguration(
            usdc.address, usdc.decimals(), ammstorage_usdc.address, ammtreasury_usdc.address, assetmngmt_usdc.address,
            spreadrouter.address, unwinding_fee_rate, unwinding_fee_treasury_portion_rate, 100,
            time_before_maturity_community, time_before_maturiy_buyer, min_liquidation_threshold_community,
            min_liquidation_threshold_buyer, min_leverage, time_after_open_wihout_unwinding,
        ),
        oracle,
        message_signer,
    )
    css_service_usdt = AmmCloseSwapServiceUsdt.deploy(
        IAmmCloseSwapLens.AmmCloseSwapServicePoolConfiguration(
            usdt.address, usdt.decimals(), ammstorage_usdt.address, ammtreasury_usdt.address, assetmngmt_usdt.address,
            spreadrouter.address, unwinding_fee_rate, unwinding_fee_treasury_portion_rate, 100,
            time_before_maturity_community, time_before_maturiy_buyer, min_liquidation_threshold_community,
            min_liquidation_threshold_buyer, min_leverage, time_after_open_wihout_unwinding,
        ),
        oracle,
        message_signer,
    )
    css_service_st_eth = AmmCloseSwapServiceStEth.deploy(
        IAmmCloseSwapLens.AmmCloseSwapServicePoolConfiguration(
            st_eth.address, st_eth.decimals(), ammstorage_st_eth.address, ammtreasury_st_eth.address, Address(0),
            steth_spread.address, unwinding_fee_rate, unwinding_fee_treasury_portion_rate, 100,
            time_before_maturity_community, time_before_maturiy_buyer, min_liquidation_threshold_community,
            min_liquidation_threshold_buyer, min_leverage, time_after_open_wihout_unwinding,
        ),
        oracle,
        message_signer,
    )
    cs_lens = AmmCloseSwapLens.deploy(
        usdt, usdc, dai, st_eth, oracle, message_signer, spreadrouter, css_service_usdt, css_service_usdc,
        css_service_dai, css_service_st_eth,
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
        IAmmGovernanceLens.AmmGovernancePoolConfiguration(dai.address, 18, ammstorage_dai.address, ammtreasury_dai.address, a.address, a.address, a.address, a.address),
        IAmmGovernanceLens.AmmGovernancePoolConfiguration(st_eth.address, st_eth.decimals(), ammstorage_st_eth.address, ammtreasury_st_eth.address, a.address, a.address, a.address, a.address),
    )
    pservice_st_eth = AmmPoolsServiceStEth.deploy(
        st_eth, weth, ipst_eth, ammtreasury_st_eth, ammstorage_st_eth, oracle, router, redeem_fee_rate,
    )
    plens_st_eth = AmmPoolsLensStEth.deploy(
        st_eth, ipst_eth, ammtreasury_st_eth, ammstorage_st_eth, oracle,
    )

    # IMPORTANT: liquidity mining contracts are not deployed & configured here
    dummy_addr = random_address()

    # finally deploy the routerrrrr
    router_impl = IporProtocolRouter.deploy(
        IporProtocolRouter.DeployedContracts(
            swaplens.address, poollens.address, amlens.address, osservice.address, osservice_st_eth.address,
            css_service_usdt.address, css_service_usdc.address, css_service_dai.address, css_service_st_eth.address,
            cs_lens.address, pservice.address, gservice.address,
            dummy_addr, dummy_addr, dummy_addr, dummy_addr,
            pservice_st_eth.address, plens_st_eth.address,
        ),
    )
    assert create3deployer.deploy_(
        b"router",
        ERC1967Proxy.get_creation_code() + Abi.encode(["address", "bytes"], [router_impl, b""])
    ).return_value == router.address
    router.initialize(False)

    return router
