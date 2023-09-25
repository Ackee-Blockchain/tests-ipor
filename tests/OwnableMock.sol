// SPDX-License-Identifier: BUSL-1.1
pragma solidity 0.8.20;

import "source/contracts/security/IporOwnable.sol";
import "source/contracts/security/IporOwnableUpgradeable.sol";
import "source/contracts/security/OwnerManager.sol";
import "source/contracts/security/PauseManager.sol";
import "source/contracts/libraries/StorageLib.sol";

contract OwnableMock is IporOwnable {
    constructor() {
        uint256 oslot = uint256(StorageLib.StorageId.Owner) + StorageLib.STORAGE_SLOT_BASE;
        address sender = _msgSender();
        assembly {
            sstore(oslot, sender)
        }
    }
    function getOwnerLibrary() external view returns (address) {
        return OwnerManager.getOwner();
    }

    function appointToOwnershipLibrary(address newAppointedOwner) external {
        require(OwnerManager.getOwner() == _msgSender(), "OwnableMock: caller is not the owner");
        OwnerManager.appointToOwnership(newAppointedOwner);
    }

    function confirmAppointmentToOwnershipLibrary() external {
        require(StorageLib.getAppointedOwner().appointedOwner == _msgSender(), "OwnableMock: caller is not the appointed owner");
        OwnerManager.confirmAppointmentToOwnership();
    }

    function renounceOwnershipLibrary() external {
        require(OwnerManager.getOwner() == _msgSender(), "OwnableMock: caller is not the owner");
        OwnerManager.renounceOwnership();
    }

    function transferOwnershipLibrary(address newOwner) external {
        require(OwnerManager.getOwner() == _msgSender(), "OwnableMock: caller is not the owner");
        OwnerManager.transferOwnership(newOwner);
    }
}

contract OwnableMockUpgradeable is IporOwnableUpgradeable {
    function initialize() external initializer {
        __Ownable_init();
        uint256 oslot = uint256(StorageLib.StorageId.Owner) + StorageLib.STORAGE_SLOT_BASE;
        address sender = _msgSender();
        assembly {
            sstore(oslot, sender)
        }
    }

    function getOwnerLibrary() external view returns (address) {
        return OwnerManager.getOwner();
    }

    function appointToOwnershipLibrary(address newAppointedOwner) external {
        require(OwnerManager.getOwner() == _msgSender(), "OwnableMock: caller is not the owner");
        OwnerManager.appointToOwnership(newAppointedOwner);
    }

    function confirmAppointmentToOwnershipLibrary() external {
        require(StorageLib.getAppointedOwner().appointedOwner == _msgSender(), "OwnableMock: caller is not the appointed owner");
        OwnerManager.confirmAppointmentToOwnership();
    }

    function renounceOwnershipLibrary() external {
        require(OwnerManager.getOwner() == _msgSender(), "OwnableMock: caller is not the owner");
        OwnerManager.renounceOwnership();
    }

    function transferOwnershipLibrary(address newOwner) external {
        require(OwnerManager.getOwner() == _msgSender(), "OwnableMock: caller is not the owner");
        OwnerManager.transferOwnership(newOwner);
    }
}