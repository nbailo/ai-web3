// SPDX-License-Identifier: MIT
pragma solidity 0.8.30;

import {Script} from "forge-std/Script.sol";

import {AquaQuoteExecutor} from "../src/AquaQuoteExecutor.sol";
import {IAqua} from "../src/interfaces/IAqua.sol";

contract AquaQuoteExecutorScript is Script {
    function run() public {
        uint256 deployerPk = vm.envUint("PRIVATE_KEY");
        address aqua = vm.envAddress("AQUA");
        address feeCollector = vm.envAddress("FEE_COLLECTOR");
        uint256 feeBps = vm.envUint("FEE_BPS");

        require(aqua != address(0), "AQUA=0");
        require(feeBps <= 10_000, "FEE_BPS");

        vm.startBroadcast(deployerPk);
        new AquaQuoteExecutor(IAqua(aqua), feeCollector, feeBps);
        vm.stopBroadcast();
    }
}
