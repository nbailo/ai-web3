import json
import os
import re
import hashlib
import time
from typing import Dict, Any, Optional, List, Tuple

# --- Configuration ---
# Simulating Unibase Membase by using a local JSON file for persistence
DB_FILE_TEMPLATE = "maker_config_{user_id}.json"
AUDIT_LOG_FILE = "maker_agent_audit.log"

# --- MOCK WEB3/CONTRACTS ---
# These classes simulate interactions with on-chain contracts (e.g., Aqua, Executor)
# They return mock data and transaction payloads as specified.

def _get_mock_tx_payload(func_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Helper to create a realistic-looking (but fake) tx payload."""
    return {
        "to": f"0x{'AquaContract' if 'aqua' in func_name else 'ExecutorContract'}",
        "data": f"0x_function_{func_name}_with_params_{params}",
        "value": 0,
        "gasLimit": 250000,
        "nonce": int(time.time())
    }

class MockAquaContract:
    """Simulates the AQUA contract specified in the spec."""
    
    def rawBalances(self, strategy_hash: str) -> Dict[str, float]:
        """Simulates reading remaining budgets for a strategy."""
        print(f"[On-Chain Read] Checking rawBalances for {strategy_hash}...")
        if strategy_hash == "0x_no_balance_hash_":
            return {}
        # Return mock balances
        return {
            "0xToken_USDC_Addr": 10000.50,
            "0xToken_WETH_Addr": 10.2
        }

    def approve(self, token_address: str, spender: str, amount: float) -> Dict[str, Any]:
        """Simulates preparing an 'approve' transaction."""
        return _get_mock_tx_payload("aqua.approve", {
            "token": token_address,
            "spender": spender,
            "amount": amount
        })

    def ship(self, executor: str, strategy_bytes: str, tokens: List[str], amounts: List[float]) -> Dict[str, Any]:
        """Simulates preparing a 'ship' transaction."""
        return _get_mock_tx_payload("aqua.ship", {
            "executor": executor,
            "strategyBytes_hash": hashlib.sha256(strategy_bytes.encode()).hexdigest()[:10],
            "tokens": tokens,
            "amounts": amounts
        })

    def dock(self, strategy_hash: str) -> Dict[str, Any]:
        """Simulates preparing a 'dock' (remove strategy) transaction."""
        return _get_mock_tx_payload("aqua.dock", {"strategyHash": strategy_hash})

class MockExecutorContract:
    """Simulates the Executor contract specified in the spec."""
    
    def setPairAllowed(self, pair_address: str, is_allowed: bool) -> Dict[str, Any]:
        """Simulates preparing a 'setPairAllowed' transaction."""
        return _get_mock_tx_payload("executor.setPairAllowed", {
            "pair": pair_address,
            "allowed": is_allowed
        })

    def setPolicy(self, policy_params: Dict[str, Any]) -> Dict[str, Any]:
        """Simulates preparing a 'setPolicy' transaction."""
        return _get_mock_tx_payload("executor.setPolicy", policy_params)

    def invalidateNoncesUpTo(self, nonce: int) -> Dict[str, Any]:
        """Simulates preparing a 'invalidateNoncesUpTo' transaction."""
        return _get_mock_tx_payload("executor.invalidateNoncesUpTo", {"nonce": nonce})

class MockWeb3Utils:
    """Simulates web3 utility functions."""
    
    def compute_strategy_hash(self, strategy_bytes: str) -> str:
        """Simulates computing the on-chain strategy hash."""
        return "0x" + hashlib.sha256(strategy_bytes.encode()).hexdigest()[:40]

    def generate_strategy_bytes(self, strategy_name: str, params: Dict[str, Any]) -> str:
        """Simulates generating the strategyBytes template."""
        return f"<strategy name='{strategy_name}' params='{json.dumps(params)}' />"

# --- MAKER AGENT CORE ---

class MakerAgent:
    """
    Implements the "Maker Agent (Chat Control Plane)" spec.
    Manages conversational state, configuration, and tx preparation.
    """
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.db_path = DB_FILE_TEMPLATE.format(user_id=self.user_id)
        
        # Core state
        self.config: Dict[str, Any] = self._load_config()
        self.pending_action: Optional[Dict[str, Any]] = None

        # Mock contract/web3 instances
        self.aqua = MockAquaContract()
        self.executor = MockExecutorContract()
        self.web3_utils = MockWeb3Utils()
        
        # A simple mapping for NLU to config keys
        self.key_map = {
            "allowed pairs": "allowed_pairs",
            "max trade size": "max_trade_size_usd",
            "daily cap": "daily_cap_usd",
            "ttl range": "ttl_range_sec",
            "spread preset": "spread_preset",
            "strategy": "active_strategy_hash"
        }
        
        print(f"MakerAgent initialized for user '{user_id}'. Config loaded from '{self.db_path}'.")

    def _get_default_config(self) -> Dict[str, Any]:
        """Returns a default config structure if no DB file is found."""
        return {
            "allowed_pairs": ["WETH-USDC", "WBTC-USDC"],
            "max_trade_size_usd": 1000.0,
            "daily_cap_usd": 10000.0,
            "ttl_range_sec": [60, 300],
            "spread_preset": "medium",
            "is_paused": True,
            "active_strategy_hash": "0x_default_strategy_hash_example_12345"
        }

    def _load_config(self) -> Dict[str, Any]:
        """
        Loads maker config from the JSON file (simulating Unibase Membase).
        """
        if not os.path.exists(self.db_path):
            print("No config file found, creating with default values.")
            cfg = self._get_default_config()
            self._save_config(cfg)
            return cfg
        
        try:
            with open(self.db_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading config: {e}. Reverting to default.")
            return self._get_default_config()

    def _save_config(self, config: Dict[str, Any]):
        """
        Saves maker config to the JSON file (simulating Unibase Membase).
        """
        try:
            with open(self.db_path, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            print(f"Error saving config: {e}")

    def _audit_log(self, action_type: str, details: Dict[str, Any]):
        """
        Writes to an audit log for all confirmed actions.
        """
        log_entry = {
            "timestamp": time.isoformat(time.gmtime()),
            "user_id": self.user_id,
            "action": action_type,
            "details": details
        }
        print(f"\n[AUDIT LOG] {log_entry['timestamp']} | {self.user_id} | {action_type} | {details}")
        try:
            with open(AUDIT_LOG_FILE, 'a') as f:
                f.write(json.dumps(log_entry) + "\n")
        except Exception as e:
            print(f"Failed to write to audit log: {e}")

    # --- 1. Natural Language Understanding (Simulation) ---
    
    def _simple_nlu(self, message: str) -> Optional[Dict[str, Any]]:
        """
        Simulates "ASI Cloud inference for natural language + tool calling".
        Uses simple regex to map chat intents to tool calls.
        """
        message = message.lower().strip()
        
        # Tool: get_status
        if re.fullmatch(r"status|show status|show config", message):
            return {"intent": "get_status"}
            
        # Tool: pause
        if re.fullmatch(r"pause|pause strategy|pause quotes", message):
            return {"intent": "pause_strategy"}

        # Tool: resume
        if re.fullmatch(r"resume|unpause|start quotes", message):
            return {"intent": "resume_strategy"}
        
        # Tool: set_config_value
        match = re.match(r"set (.*) to (.*)", message)
        if match:
            key, value = match.groups()
            return {"intent": "set_config_value", "key": key.strip(), "value": value.strip()}
        
        # Tool: prepare_onboarding_txs
        match = re.match(r"onboard (.*) with (.*) (.*)", message)
        if match:
            name, amount, token = match.groups()
            return {"intent": "prepare_onboarding", "name": name, "amount": amount, "token": token}

        # Tool: prepare_executor_policy_tx (setPairAllowed)
        match = re.match(r"allow pair (.*)", message)
        if match:
            return {"intent": "set_pair_allowed", "pair": match.group(1), "allowed": True}
        
        match = re.match(r"disallow pair (.*)", message)
        if match:
            return {"intent": "set_pair_allowed", "pair": match.group(1), "allowed": False}

        return None # Unknown intent

    # --- 2. Tool-Callable Methods (Agent Responsibilities) ---

    def get_status(self) -> str:
        """[Tool] Responds with active strategies and remaining budgets."""
        hash = self.config.get("active_strategy_hash", "0x_no_balance_hash_")
        budgets = self.aqua.rawBalances(hash)
        
        status_report = [
            "--- Maker Agent Status ---",
            f"User: {self.user_id}",
            f"Status: {'PAUSED' if self.config.get('is_paused') else 'ACTIVE'}",
            "\n[Configuration]",
            f"  - Allowed Pairs: {self.config.get('allowed_pairs')}",
            f"  - Max Trade Size: ${self.config.get('max_trade_size_usd')}",
            f"  - Daily Cap: ${self.config.get('daily_cap_usd')}",
            f"  - Spread Preset: {self.config.get('spread_preset')}",
            f"  - Active Strategy: {hash}",
            "\n[On-Chain Budgets]",
        ]
        if budgets:
            for token, amount in budgets.items():
                status_report.append(f"  - {token}: {amount}")
        else:
            status_report.append("  - No budgets found for active strategy.")
            
        return "\n".join(status_report)

    def _parse_config_value(self, key: str, str_value: str) -> Any:
        """Safely parses string values from NLU into correct types."""
        if key == "allowed_pairs":
            return [pair.strip().upper() for pair in str_value.split(",")]
        if key in ["max_trade_size_usd", "daily_cap_usd"]:
            return float(re.sub(r"[,$]", "", str_value))
        if key == "ttl_range_sec":
            return [int(t.strip()) for t in str_value.split("-")]
        if key == "is_paused":
            return str_value.lower() in ['true', '1', 'yes']
        return str_value # For spread_preset, active_strategy_hash

    def propose_config_update(self, raw_key: str, str_value: str) -> str:
        """[Tool] Proposes a change to the MakerConfig."""
        if raw_key not in self.key_map:
            return f"Error: I don't know how to set '{raw_key}'. Valid keys are: {list(self.key_map.keys())}"
        
        key = self.key_map[raw_key]
        
        try:
            value = self._parse_config_value(key, str_value)
        except Exception as e:
            return f"Error: Invalid format for '{raw_key}'. Failed to parse '{str_value}'. ({e})"
        
        # Set pending action for confirmation
        self.pending_action = {
            "type": "update_config",
            "key": key,
            "value": value
        }
        
        return f"OK. I am ready to update '{key}' to '{value}'.\nPlease type 'confirm' to apply this change."

    def propose_pause_or_resume(self, pause: bool) -> str:
        """[Tool] Proposes pausing or resuming the strategy."""
        action_str = "pause" if pause else "resume"
        self.pending_action = {
            "type": "update_config",
            "key": "is_paused",
            "value": pause
        }
        return f"OK. I am ready to {action_str} all quoting strategies.\nPlease type 'confirm' to apply this change."

    def propose_onboarding(self, name: str, amount: str, token: str) -> str:
        """[Tool] Prepares a new strategy for shipping."""
        try:
            amount_float = float(amount)
        except ValueError:
            return f"Error: Invalid amount '{amount}'."
        
        # Simulate onboarding assistant logic
        params = {"pair": "WETH-USDC", "spread": 0.005} # Example params
        strategy_bytes = self.web3_utils.generate_strategy_bytes(name, params)
        strategy_hash = self.web3_utils.compute_strategy_hash(strategy_bytes)
        
        self.pending_action = {
            "type": "onboard_strategy",
            "name": name,
            "bytes": strategy_bytes,
            "hash": strategy_hash,
            "token": token.upper(),
            "amount": amount_float
        }
        
        summary = [
            f"OK. I am ready to onboard strategy '{name}'.",
            f"  - Generated strategyBytes (hash: {strategy_hash})",
            "  - This will prepare 3 transactions:",
            f"    1. approve(AQUA, {token.upper()}, {amount_float})",
            f"    2. ship(executor, {strategy_hash}, [{token.upper()}], [{amount_float}])",
            f"    3. dock(OLD_STRATEGY_HASH) (to replace current)",
            "\nPlease type 'confirm' to generate these transaction payloads."
        ]
        return "\n".join(summary)

    def propose_set_pair_allowed(self, pair: str, allowed: bool) -> str:
        """[Tool] Prepares a tx to allow/disallow a pair on the executor."""
        action_str = "allow" if allowed else "disallow"
        self.pending_action = {
            "type": "set_pair_allowed",
            "pair_address": f"0x_addr_for_{pair.upper()}",
            "is_allowed": allowed
        }
        
        summary = [
            f"OK. I am ready to {action_str} the pair '{pair.upper()}' on the executor.",
            "  - This will prepare 1 transaction:",
            f"    1. setPairAllowed({self.pending_action['pair_address']}, {allowed})",
            "\nPlease type 'confirm' to generate this transaction payload."
        ]
        return "\n".join(summary)

    # --- 3. Safety: Confirmation Logic ---

    def confirm_action(self) -> str:
        """
        Executes the pending action after 'confirm' is received.
        This is the only function that mutates state or produces txs.
        """
        if not self.pending_action:
            return "There is no action to confirm."
            
        action = self.pending_action
        self.pending_action = None # Clear action *before* execution
        
        try:
            # --- Handle Config Update ---
            if action["type"] == "update_config":
                key = action['key']
                value = action['value']
                self.config[key] = value
                self._save_config(self.config)
                self._audit_log("config_update", {"key": key, "value": value})
                return f"Success. Configuration updated: '{key}' is now '{value}'."

            # --- Handle Onboarding TX Prep ---
            elif action["type"] == "onboard_strategy":
                old_hash = self.config.get("active_strategy_hash")
                
                # 1. Prepare approve tx
                tx_approve = self.aqua.approve(
                    token_address=f"0x_addr_for_{action['token']}",
                    spender="0xAquaContract",
                    amount=action['amount']
                )
                # 2. Prepare ship tx
                tx_ship = self.aqua.ship(
                    executor="0xExecutorContract",
                    strategy_bytes=action['bytes'],
                    tokens=[f"0x_addr_for_{action['token']}"],
                    amounts=[action['amount']]
                )
                # 3. Prepare dock tx (to remove old strategy)
                tx_dock = self.aqua.dock(old_hash)
                
                # 4. Update config to point to new strategy
                self.config["active_strategy_hash"] = action['hash']
                self._save_config(self.config)
                
                self._audit_log("tx_prep.onboard", action)
                
                response = [
                    "Success. Payloads generated. Please sign and send these transactions:",
                    f"\n[TX 1: APPROVE]\n{json.dumps(tx_approve, indent=2)}",
                    f"\n[TX 2: SHIP NEW STRATEGY]\n{json.dumps(tx_ship, indent=2)}",
                    f"\n[TX 3: DOCK OLD STRATEGY]\n{json.dumps(tx_dock, indent=2)}",
                    f"\nConfig updated. Active strategy is now: {action['hash']}"
                ]
                return "\n".join(response)

            # --- Handle Executor Policy TX Prep ---
            elif action["type"] == "set_pair_allowed":
                tx_set_pair = self.executor.setPairAllowed(
                    pair_address=action['pair_address'],
                    is_allowed=action['is_allowed']
                )
                self._audit_log("tx_prep.set_pair", action)
                response = [
                    "Success. Payload generated. Please sign and send this transaction:",
                    f"\n[TX 1: SET PAIR ALLOWED]\n{json.dumps(tx_set_pair, indent=2)}"
                ]
                return "\n".join(response)

            else:
                return "Error: Unknown confirmed action type."

        except Exception as e:
            self.pending_action = None # Ensure state is clean on error
            return f"An error occurred during confirmation: {e}"

    def cancel_action(self) -> str:
        """Cancels any pending action."""
        if not self.pending_action:
            return "There is no action to cancel."
        
        self.pending_action = None
        return "Pending action cancelled."

    # --- 4. Main Chat Handler ---
    
    def handle_message(self, message: str) -> str:
        """
        Main entry point for the conversational interface.
        Routes user input to the correct logic.
        """
        
        # 1. Handle special commands (confirm/cancel)
        if message.lower().strip() == "confirm":
            return self.confirm_action()
            
        if message.lower().strip() == "cancel":
            return self.cancel_action()
            
        # 2. Safety check: Don't allow new actions if one is pending
        if self.pending_action:
            return "You have a pending action. Please type 'confirm' or 'cancel'."
            
        # 3. Pass message to NLU
        intent_data = self._simple_nlu(message)
        
        if not intent_data:
            return "Sorry, I don't understand that request. Try 'status', 'pause', or 'set <key> to <value>'."
            
        # 4. Route intent to the correct "propose_" method
        intent = intent_data.get("intent")
        
        try:
            if intent == "get_status":
                return self.get_status()
            
            if intent == "pause_strategy":
                return self.propose_pause_or_resume(pause=True)

            if intent == "resume_strategy":
                return self.propose_pause_or_resume(pause=False)
                
            if intent == "set_config_value":
                return self.propose_config_update(intent_data['key'], intent_data['value'])
                
            if intent == "prepare_onboarding":
                return self.propose_onboarding(intent_data['name'], intent_data['amount'], intent_data['token'])
                
            if intent == "set_pair_allowed":
                return self.propose_set_pair_allowed(intent_data['pair'], intent_data['allowed'])
                
            return "Sorry, that intent is not fully implemented."
            
        except Exception as e:
            return f"An error occurred while processing your request: {e}"


# --- Main Execution Loop ---
if __name__ == "__main__":
    print("--- Aqua Maker Agent (Chat Control Plane) ---")
    print("Type 'exit' to quit.")
    print("Type 'status' to see your config.")
    print("Example commands:")
    print("  > status")
    print("  > pause")
    print("  > resume")
    print("  > set max trade size to 25000")
    print("  > set allowed pairs to WETH-USDC, WBTC-USDC")
    print("  > allow pair WBTC-WETH")
    print("  > onboard my_new_strategy with 50.5 WETH")
    print("-" * 45)
    
    # Use a hardcoded user ID for this simulation
    agent = MakerAgent(user_id="maker_001")
    
    while True:
        try:
            message = input("\nMaker > ")
            
            if message.lower().strip() == "exit":
                print("Exiting agent. Goodbye.")
                break
                
            if not message.strip():
                continue
                
            response = agent.handle_message(message)
            print(f"\nAgent:\n{response}")
            
        except EOFError:
            print("\nExiting agent. Goodbye.")
            break
        except KeyboardInterrupt:
            print("\nExiting agent. Goodbye.")
            break