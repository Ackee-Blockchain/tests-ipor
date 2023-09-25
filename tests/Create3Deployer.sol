// SPDX-License-Identifier: MIT

import "./Create3.sol";

contract Create3Deployer {
    function deploy(bytes32 salt, bytes memory bytecode) public returns (address) {
        return Create3.create3(salt, bytecode);
    }

    function getAddress(bytes32 salt) public view returns (address) {
        return Create3.addressOf(salt);
    }
}