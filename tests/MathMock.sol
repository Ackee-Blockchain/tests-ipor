// SPDX-License-Identifier: BUSL-1.1
pragma solidity 0.8.20;

import "source/contracts/libraries/math/IporMath.sol";

contract MathMock {
    function division(uint256 x, uint256 y) external pure returns (uint256) {
        return IporMath.division(x, y);
    }

    function divisionInt(int256 x, int256 y) external pure returns (int256) {
        return IporMath.divisionInt(x, y);
    }
}