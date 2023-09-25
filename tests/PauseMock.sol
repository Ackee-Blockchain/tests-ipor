// SPDX-License-Identifier: BUSL-1.1
pragma solidity 0.8.20;

import "source/contracts/security/PauseManager.sol";

contract PauseMock {
    
    function addPauseGuardian(address _guardian) external {
        PauseManager.addPauseGuardian(_guardian);
    }

    function removePauseGuardian(address _guardian) external {
        PauseManager.removePauseGuardian(_guardian);
    }

    function isPauseGuardian(address _guardian) external view returns (bool) {
        return PauseManager.isPauseGuardian(_guardian);
    }
}