from wake.testing import *

from pytypes.tests.OwnableMock import OwnableMock, OwnableMockUpgradeable
from .utils import deploy_with_proxy

@default_chain.connect()
def test_ownable():
    owner = default_chain.accounts[0]
    default_chain.set_default_accounts(owner)

    # deploy contract
    ownable = OwnableMock.deploy()
    assert ownable.owner() == owner.address

    # transfer ownership
    new_owner = default_chain.accounts[1]
    ownable.transferOwnership(new_owner)
    assert ownable.owner() == owner.address

    # confirm ownership
    ownable.confirmTransferOwnership(from_=new_owner)
    assert ownable.owner() == new_owner.address

    # renounce ownership
    ownable.renounceOwnership(from_=new_owner)
    assert ownable.owner() == Address.ZERO

@default_chain.connect()
def test_ownable_upgradeable():
    owner = default_chain.accounts[0]
    default_chain.set_default_accounts(owner)

    # deploy upgradeable contract
    ownable = deploy_with_proxy(OwnableMockUpgradeable)
    ownable.initialize()
    assert ownable.owner() == owner.address

    # transfer ownership
    new_owner = default_chain.accounts[1]
    ownable.transferOwnership(new_owner)
    assert ownable.owner() == owner.address

    # confirm ownership
    ownable.confirmTransferOwnership(from_=new_owner)
    assert ownable.owner() == new_owner.address

    # renounce ownership
    ownable.renounceOwnership(from_=new_owner)
    assert ownable.owner() == Address.ZERO

@default_chain.connect()
def test_owner_manager():
    owner = default_chain.accounts[0]
    default_chain.set_default_accounts(owner)

    # deploy contract
    ownable = OwnableMock.deploy()
    assert ownable.getOwnerLibrary() == owner.address

    # transfer ownership
    new_owner = default_chain.accounts[1]
    ownable.transferOwnershipLibrary(new_owner)
    assert ownable.getOwnerLibrary() == new_owner.address

    # appoint ownership
    ownable.appointToOwnershipLibrary(owner, from_=new_owner)
    assert ownable.getOwnerLibrary() == new_owner.address

    # confirm ownership
    ownable.confirmAppointmentToOwnershipLibrary(from_=owner)
    assert ownable.getOwnerLibrary() == owner.address

    # renounce ownership
    ownable.renounceOwnershipLibrary(from_=owner)
    assert ownable.getOwnerLibrary() == Address.ZERO

@default_chain.connect()
def test_owner_manager_upgradeable():
    owner = default_chain.accounts[0]
    default_chain.set_default_accounts(owner)

    # deploy contract
    ownable = OwnableMockUpgradeable.deploy()
    ownable.initialize()
    assert ownable.getOwnerLibrary() == owner.address

    # transfer ownership
    new_owner = default_chain.accounts[1]
    ownable.transferOwnershipLibrary(new_owner)
    assert ownable.getOwnerLibrary() == new_owner.address

    # appoint ownership
    ownable.appointToOwnershipLibrary(owner, from_=new_owner)
    assert ownable.getOwnerLibrary() == new_owner.address

    # confirm ownership
    ownable.confirmAppointmentToOwnershipLibrary(from_=owner)
    assert ownable.getOwnerLibrary() == owner.address

    # renounce ownership
    ownable.renounceOwnershipLibrary(from_=owner)
    assert ownable.getOwnerLibrary() == Address.ZERO