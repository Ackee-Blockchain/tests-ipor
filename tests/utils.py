from typing import Union

from wake.testing import Address, Account, default_chain, keccak256, Abi
from pytypes.openzeppelin.contracts.proxy.ERC1967.ERC1967Proxy import ERC1967Proxy


def deploy_with_proxy(contract):
    impl = contract.deploy()
    proxy = ERC1967Proxy.deploy(impl, b"")
    return contract(proxy)


def mint(token: Union[Address, Account], to: Union[Address, Account], amount: int):
    if isinstance(token, Account):
        token = token.address
    if isinstance(to, Account):
        to = to.address

    if token == Address("0x6B175474E89094C44Da98b954EedeAC495271d0F"):
        # DAI
        total_supply_slot = 1
        balance_slot = int.from_bytes(keccak256(Abi.encode(["address", "uint256"], [to, 2])), byteorder="big")
    elif token == Address("0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"):
        # USDC
        total_supply_slot = 11
        balance_slot = int.from_bytes(keccak256(Abi.encode(["address", "uint256"], [to, 9])), byteorder="big")
    elif token == Address("0xdac17f958d2ee523a2206206994597c13d831ec7"):
        # USDT
        total_supply_slot = 1
        balance_slot = int.from_bytes(keccak256(Abi.encode(["address", "uint256"], [to, 2])), byteorder="big")
    else:
        raise ValueError(f"Unknown token {token}")

    old_total_supply = int.from_bytes(default_chain.chain_interface.get_storage_at(str(token), total_supply_slot), byteorder="big")
    default_chain.chain_interface.set_storage_at(str(token), total_supply_slot, (old_total_supply + amount).to_bytes(32, "big"))

    old_balance = int.from_bytes(default_chain.chain_interface.get_storage_at(str(token), balance_slot), byteorder="big")
    default_chain.chain_interface.set_storage_at(str(token), balance_slot, (old_balance + amount).to_bytes(32, "big"))
