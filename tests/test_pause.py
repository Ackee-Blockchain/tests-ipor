from woke.testing import *

from pytypes.tests.PauseMock import PauseMock
from .utils import deploy_with_proxy

@default_chain.connect()
def test_pause():
    owner = default_chain.accounts[0]
    default_chain.set_default_accounts(owner)

    # deploy contract
    pause = PauseMock.deploy()
    
    # add
    assert pause.isPauseGuardian(owner.address) == False
    pause.addPauseGuardian(owner)
    assert pause.isPauseGuardian(owner.address) == True
    
    # remove
    pause.removePauseGuardian(owner)
    assert pause.isPauseGuardian(owner.address) == False