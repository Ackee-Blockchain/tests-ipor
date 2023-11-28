from wake.testing import *
from pytypes.source.contracts.interfaces.types.IporRiskManagementOracleTypes import IporRiskManagementOracleTypes
from pytypes.source.contracts.libraries.RiskManagementLogic import RiskManagementLogic
from pytypes.source.contracts.oracles.IporOracle import IporOracle
from pytypes.source.contracts.oracles.IporRiskManagementOracle import IporRiskManagementOracle
from pytypes.source.contracts.oracles.OraclePublisher import OraclePublisher
from pytypes.source.contracts.oracles.libraries.IporRiskManagementOracleStorageTypes import IporRiskManagementOracleStorageTypes
from pytypes.openzeppelin.contracts.token.ERC20.ERC20 import ERC20
from pytypes.openzeppelin.contracts.proxy.ERC1967.ERC1967Proxy import ERC1967Proxy

def setup_oracle(dai, usdc, usdt):
    oracle = IporOracle.deploy(usdt, 22, usdc, 21, dai, 23)
    proxy = ERC1967Proxy.deploy(oracle, b"")
    oracle = IporOracle(proxy)
    oracle.initialize([dai], [1])

    riskmng = IporRiskManagementOracle.deploy()
    proxy = ERC1967Proxy.deploy(riskmng, b"")
    riskmng = IporRiskManagementOracle(proxy)
    riskmng.initialize([dai], [IporRiskManagementOracleTypes.RiskIndicators(10000, 10000, 10, 10, 10)], [IporRiskManagementOracleTypes.BaseSpreadsAndFixedRateCaps(100, 150, 200, 300, 350, 480, 600, 800, 900, 1000, 1500, 2000)])

    publisher = OraclePublisher.deploy(oracle,riskmng)
    proxy = ERC1967Proxy.deploy(publisher, b"")
    publisher = OraclePublisher(proxy)
    publisher.initialize()

    return oracle, riskmng, publisher

def revert_handler(e: TransactionRevertedError):
    if e.tx is not None:
        print(e.tx.call_trace)
        print(e.tx.console_logs)

@default_chain.connect()
@on_revert(revert_handler)
def test_pause():
    owner = default_chain.accounts[0]
    default_chain.set_default_accounts(owner)

    # deploy tokens
    usdt = ERC20.deploy("USDT", "USDT") # not equal
    usdc = ERC20.deploy("USDC", "USDC")
    dai = ERC20.deploy("DAI", "DAI")

    # deploy components
    oracle, riskmng, publisher = setup_oracle(dai, usdc, usdt)

    # interactions
    print(oracle.getIndex(dai))
    print(oracle.getAccruedIndex(2,dai))

    assert oracle.isUpdater(owner) == 0
    oracle.addUpdater(owner)
    assert oracle.isUpdater(owner) == 1

    tx = oracle.updateIndex(dai, 100)
    print(tx.console_logs)
    print(oracle.getAccruedIndex(1786747203,dai))

    tx = oracle.updateIndex(dai, 200)
    print(tx.console_logs)
    print(oracle.getAccruedIndex(1786747203,dai))

    tx = oracle.updateIndex(dai, 300)
    print(tx.console_logs)
    print(oracle.getAccruedIndex(1786747203,dai))

    print(oracle.getIndex(dai))

    print(oracle.calculateAccruedIbtPrice(dai, 1786747203))

    # publisher
    oracle.addUpdater(publisher)
    publisher.addUpdater(owner)
    print(IporOracle.updateIndex.selector)
    publisher.publish([oracle], [Abi.encode_with_selector(IporOracle.updateIndex.selector, ["address", "uint256"], [dai, 400])])
    print(oracle.getIndex(dai))

    print(oracle.address)
    print(riskmng.address)
    print(publisher.address)

    # risk management
