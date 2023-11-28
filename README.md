# Tests for IPOR
This repository serves as an example of tests written in a development and testing framework called [Wake](https://github.com/Ackee-Blockchain/wake).

![horizontal splitter](https://github.com/Ackee-Blockchain/wake-detect-action/assets/56036748/ec488c85-2f7f-4433-ae58-3d50698a47de)

## Setup

1. Clone this repository
2. `git submodule update --init --recursive` if not cloned with `--recursive`
3. `cd source && npm install && cd ..` to install dependencies
4. `wake init pytypes` to generate pytypes
5. `wake test` to run tests

Tested with `wake` version `4.0.0` and `anvil` version `0.1.0 (25d3ce7 2023-08-01T00:20:13.496244391Z)`. Some of the tests expect a local full node at http://localhost:8545 with the Ethereum mainnet at block 18179103 running.
