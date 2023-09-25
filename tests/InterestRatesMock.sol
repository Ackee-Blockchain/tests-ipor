import "source/contracts/libraries/math/InterestRates.sol";

contract InterestRatesMock {
    function addContinuousCompoundInterestUsingRatePeriodMultiplication(
        uint256 value,
        uint256 interestRatePeriodMultiplication
    ) public pure returns (uint256) {
        return InterestRates.addContinuousCompoundInterestUsingRatePeriodMultiplication(
            value,
            interestRatePeriodMultiplication
        );
    }
}