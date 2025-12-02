import os
import json
import requests
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict, field
import datetime
import re

# Revised trigger logic for two-tiered intent separation
EXPLICIT_EXECUTE_TERMS = [
    'execute', 'proceed', 'set now', 'start trading', 'activate',
    'make this change', 'place trade now', 'apply change', 'confirm and proceed',
    'add and activate', 'trade now', 'enable', 'save settings', 'update now', 'commit'
]

# LLM prompt now explicitly describes the difference
LLM_CLASSIFY_PROMPT = """
You are a safety-conscious Aqua Maker assistant. For every user message, classify the intent as one of:
- 'enquiry': The user asks about trading, pairs, config, wants examples, expresses interest/curiosity, OR uses phrases like "i would like to", "i want to", "can i", "help me set up", "what are", "can you give me examples", "set up" WITHOUT explicit execution terms (e.g. 'I want to trade USD/ETH', 'How do I set up trading?', 'Can I use ETH?', 'Tell me about pairs', 'what are some examples of trading pairs', 'can you give me examples', 'i would like to set an order for DIA/USDC', 'i want to set up a trading pair', 'set up usd trading pair')
- 'action': The user UNAMBIGUOUSLY instructs you to EXECUTE/PROCEED with a config or transaction. This must include direct intent: ('execute', 'set now', 'commit', 'please start trading', 'activate this', 'do this now', etc) plus at least one config/tx parameter (trading pair, size, etc)
- 'help': User is lost, confused, or asks for assistance
- 'smalltalk': Casual chit-chat/greeting
- 'confirm': The user confirms a pending action (e.g. 'confirm', 'yes, do it', 'approve this change', 'please execute', 'go ahead')
Always reply as JSON: {"intent": "...", "response": "..."}
IMPORTANT: 
- Questions asking for examples, information, or "what are" should ALWAYS be classified as 'enquiry'
- Phrases like "i would like to", "i want to set", "help me set up", "set up" WITHOUT words like "execute", "set now", "activate" should be classified as 'enquiry', not 'action'
- Only classify as 'action' if the user explicitly says to execute/proceed/activate
- If the message is anything BUT a direct command to execute, respond with a helpful answer, not an action or transaction
"""

# ---- Config from environment ----
LLM_API_ENDPOINT = os.getenv("LLM_API_ENDPOINT", "https://api.asi1.ai/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY", "sk_d95b81ac6db6406a82c9ba3baf078fa207b863c9a0d3422292c05033a3a2f397")
LLM_MODEL = os.getenv("LLM_MODEL", "asi1-extended")

headers = {
    "Authorization": f"Bearer {LLM_API_KEY}",
    "Content-Type": "application/json",
}

# --- DATA MODELS ---

@dataclass
class MakerConfig:
    allowed_pairs: List[str] = field(default_factory=list)
    max_trade_size: Optional[float] = None
    daily_caps: Dict[str, float] = field(default_factory=dict)
    ttl_ranges: Dict[str, Any] = field(default_factory=dict)  # Can be adjusted for real structure
    spread_presets: Dict[str, float] = field(default_factory=dict)
    paused: bool = False
    strategy: Optional[str] = None
    strategyBytes: Optional[str] = None  # Placeholder for bytes, e.g. base64 string
    strategyHash: Optional[str] = None

@dataclass
class TransactionPayload:
    payload_type: str  # e.g., 'approve', 'ship', 'dock', etc.
    abi_encoded_data: str  # Placeholder for ABI-encoded data (could be hex or descriptive for simulation)
    summary: str  # Human-readable summary
    state: str = "pending"  # 'pending', 'confirmed', 'cancelled'
    created_at: str = field(default_factory=lambda: datetime.datetime.utcnow().isoformat())
    confirmed_by: Optional[str] = None
    confirmed_at: Optional[str] = None

@dataclass
class AuditLogEntry:
    intent: str
    payload: dict
    confirmation: Optional[dict] = None
    timestamp: str = field(default_factory=lambda: datetime.datetime.utcnow().isoformat())
    state: str = "pending"  # 'pending', 'confirmed', 'cancelled'

# Helper functions to load/dump these as JSON objects can be added as needed.

# (All order summary schema, prompt, test payload, legacy output, and parsed demo JSON code removed.)
# Only MakerAgent and Aqua config/payload/audit log logic is present. No legacy schemas, prompts, or test outputs remain.

MAKER_CONFIG_FILE = 'maker_config.json'
AUDIT_LOG_FILE = 'audit_log.json'

def save_maker_config(config: MakerConfig):
    with open(MAKER_CONFIG_FILE, 'w') as f:
        json.dump(asdict(config), f, indent=2)

def load_maker_config() -> MakerConfig:
    try:
        with open(MAKER_CONFIG_FILE, 'r') as f:
            data = json.load(f)
            return MakerConfig(**data)
    except FileNotFoundError:
        return MakerConfig()
    except Exception as e:
        print('Failed to load maker config:', e)
        return MakerConfig()

def append_audit_log(entry: AuditLogEntry):
    try:
        logs = load_audit_log()
    except Exception:
        logs = []
    logs.append(asdict(entry))
    with open(AUDIT_LOG_FILE, 'w') as f:
        json.dump(logs, f, indent=2)

def load_audit_log() -> list:
    try:
        with open(AUDIT_LOG_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return []
    except Exception as e:
        print('Failed to load audit log:', e)
        return []

def is_maker_intent(message: str) -> Optional[str]:
    """
    Quick pattern match for demo; real logic may use NLP/LLM.
    Returns type: 'config' or 'tx', or None if not relevant.
    """
    config_keywords = [
        'allowed pair', 'max trade', 'daily cap', 'ttl', 'spread', 'pause', 'strategy', 'policy', 'set', 'update'
    ]
    tx_keywords = [
        'approve', 'ship', 'dock', 'invalidate', 'execute', 'sign', 'payload']
    lm = message.lower()
    for word in config_keywords:
        if word in lm:
            return 'config'
    for word in tx_keywords:
        if word in lm:
            return 'tx'
    return None

def summary_for_intent(message: str, detected: str) -> str:
    # Very simple summary maker, could be replaced by LLM or deep parser.
    if detected == 'config':
        return f"Configuration update: {message}"
    elif detected == 'tx':
        return f"Transaction action: {message}"
    return message

def build_tx_payload(message: str, detected: str) -> TransactionPayload:
    summary = summary_for_intent(message, detected)
    simulated_abi = f"abi_encoded({message[:24]})"  # demo placeholder
    return TransactionPayload(
        payload_type=detected,
        abi_encoded_data=simulated_abi,
        summary=summary,
    )

def build_audit_entry(message: str, payload: TransactionPayload) -> AuditLogEntry:
    return AuditLogEntry(
        intent=message,
        payload=asdict(payload),
        confirmation=None,
        state="pending"
    )

# --- Safety Guardrails: Only act on explicit commands and confirmations ---

REQUIRED_ACTION_KEYWORDS = ["pair", "trade", "strategy", "cap", "allow", "ttl", "spread", "pause", "approve", "dock", "ship", "invalidate", "amount"]


def has_required_details(message: str):
    # Requires BOTH an explicit execute/commit/proceed term and a valid config param
    lmsg = message.lower()
    has_explicit = any(term in lmsg for term in EXPLICIT_EXECUTE_TERMS)
    has_pair = re.search(r'\b[A-Z]{2,6}/[A-Z]{2,6}\b', message)
    has_amount = re.search(r'\b\d+\b', message)
    has_config_kw = any(x in lmsg for x in ["allowed pair", "max trade", "spread", "daily cap", "ttl", "strategy", "limit", "policy"][0:])
    # Only treat as actionable if explicit command (e.g., 'execute trade USD/ETH now')
    return has_explicit and (has_pair or has_config_kw or has_amount)

# --- Fetch.ai Agent Handler Template (for dynamic, message-based workflow) ---

class MakerAgent:
    """
    Template class for a fetch.ai message-based agent that updates Aqua Maker config/state securely.

    REQUIRED:
    - Integrate with fetch.ai agent runtime according to your platform (AEA, Fetch SDK, etc).
    - All communication is over fetch.ai messages; NO use of input(), print(), static prompts, schemas.
    - Uses LLM_API_ENDPOINT, LLM_API_KEY, LLM_MODEL config for all AI completions/parsing.
    """
    def __init__(self, llm_endpoint, llm_key, llm_model):
        self.llm_endpoint = llm_endpoint
        self.llm_key = llm_key
        self.llm_model = llm_model
        self.pending_payload = None
        self.pending_audit = None
        self.histories = {}  # sender_id: list of (role, content)

    def update_history(self, sender, role, message):
        if sender not in self.histories:
            self.histories[sender] = []
        self.histories[sender].append((role, message))
        self.histories[sender] = self.histories[sender][-10:]  # keep only last 10 messages

    def get_context(self, sender):
        return [
            {"role": r, "content": m}
            for r, m in self.histories.get(sender, [])
        ]

    def handle_message(self, message, sender):
        # Add current user message to the conversation history before processing
        self.update_history(sender, "user", message)
        context = self.get_context(sender)
        classification = classify_user_intent_llm(self, message, context)
        intent = classification.get("intent", None)
        extra_response = classification.get("response", "")

        # --- Confirmation logic as before ---
        if intent == "confirm":
            if self.pending_payload and self.pending_audit:
                last_summary = self.pending_payload.summary.strip().lower() if self.pending_payload and self.pending_payload.summary else ""
                lmsg = message.strip().lower()
                if lmsg == "confirm" or (last_summary and last_summary in lmsg):
                    who = sender
                    now = datetime.datetime.utcnow().isoformat()
                    self.pending_payload.state = 'confirmed'
                    self.pending_payload.confirmed_by = who
                    self.pending_payload.confirmed_at = now
                    self.pending_audit.state = 'confirmed'
                    self.pending_audit.confirmation = {'by': who, 'at': now}
                    append_audit_log(self.pending_audit)
                    out = {
                        'type': 'confirmed_action',
                        'payload': asdict(self.pending_payload),
                        'audit_log_entry': asdict(self.pending_audit),
                        'info': 'Audit log updated. No on-chain TX executed (demo).'
                    }
                    self.send_message(sender, out)
                    # Update conversation history with agent response
                    self.update_history(sender, "assistant", json.dumps(out))
                    self.pending_payload = None
                    self.pending_audit = None
                else:
                    out = {
                        'type': 'confirm_needed',
                        'info': f"To confirm, please reply with: confirm {last_summary}"
                    }
                    self.send_message(sender, out)
                    self.update_history(sender, "assistant", json.dumps(out))
            else:
                out = {
                    'type': 'no_pending_action',
                    'info': "There's nothing pending confirmation."
                }
                self.send_message(sender, out)
                self.update_history(sender, "assistant", json.dumps(out))
            return

        # --- Pending action creation guardrail ---
        if intent == 'action':
            if has_required_details(message):
                payload = build_tx_payload(message, intent)
                audit_entry = build_audit_entry(message, payload)
                self.pending_payload = payload
                self.pending_audit = audit_entry
                out = {
                    'type': 'pending_action',
                    'summary': payload.summary,
                    'abi_encoded_data': payload.abi_encoded_data,
                    'instruction': f'Reply with "confirm {payload.summary}" to execute.'
                }
                self.send_message(sender, out)
                self.update_history(sender, "assistant", json.dumps(out))
            else:
                out = {
                    'type': 'clarification_needed',
                    'info': "To create or update a config/transaction, please specify the trading pair, amount, and action you want to perform."
                }
                self.send_message(sender, out)
                self.update_history(sender, "assistant", json.dumps(out))
            return

        # --- Help/enquiry/smalltalk/unknown/fallback ---
        if intent in ("help", "smalltalk", "enquiry", "unknown"):
            out = {'type': intent, 'info': extra_response}
            self.send_message(sender, out)
            self.update_history(sender, "assistant", json.dumps(out))
        else:
            # Fallback: Detect questions, examples requests, or non-execution intent
            lmsg = message.lower()
            has_pair = re.search(r'\b[A-Z]{2,6}/[A-Z]{2,6}\b', message)
            has_execute = any(term in lmsg for term in EXPLICIT_EXECUTE_TERMS)
            
            # Check for question words or example requests
            question_words = ['what', 'how', 'can you', 'could you', 'would you', 'examples', 'example', 'show me', 'tell me', 'explain']
            is_question = any(word in lmsg for word in question_words) or message.strip().endswith('?')
            
            # Check for setup/configuration intent without execution
            setup_phrases = ['set up', 'setup', 'configure', 'create', 'add', 'want to', 'would like to']
            has_setup_intent = any(phrase in lmsg for phrase in setup_phrases) and not has_execute
            
            if is_question or has_setup_intent or (has_pair and not has_execute):
                # User is asking questions or expressing interest, not executing - treat as enquiry
                if 'example' in lmsg or 'examples' in lmsg:
                    out = {'type': 'enquiry', 'info': "Great question! Some popular trading pairs you can use include: DAI/USDC, ETH/USD, BTC/USD, USDT/USDC, and AQUA/USDT. These are stable, liquid pairs that work well for automated trading. Would you like to know more about any specific pair, or help setting one up?"}
                elif has_setup_intent:
                    out = {'type': 'enquiry', 'info': "I'd be happy to help you set that up! To proceed, please specify: the exact trading pair (e.g., DAI/USDC), the amount you want to trade, and say 'execute' or 'set now' when you're ready to confirm. Would you like guidance on any of these?"}
                else:
                    out = {'type': 'enquiry', 'info': "I'm here to help! Could you tell me more about what you'd like to know or set up? For example, I can help with trading pairs, configuration, or explain how Aqua Maker works."}
            else:
                out = {'type': 'unsupported', 'info': "I'm not sure what you want to do. Try 'help' or ask for an example."}
            self.send_message(sender, out)
            self.update_history(sender, "assistant", json.dumps(out))

    def send_message(self, recipient, data):
        """
        Implement your fetch.ai message send here (e.g., flask, websocket, AEA handler, etc).
        recipient: str (receiver agent name/user)
        data: dict (can be serialized as JSON)
        """
        # This is a placeholder for your agent's actual message sending logic:
        pass

# Update classify_user_intent_llm to use message context

def classify_user_intent_llm(agent, message, context):
    # Fix: system prompt always comes first, then chat history, then current user message
    endpoint = agent.llm_endpoint
    key = agent.llm_key
    model = agent.llm_model
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    prompt_messages = [
        {"role": "system", "content": LLM_CLASSIFY_PROMPT}
    ]
    prompt_messages += context
    prompt_messages.append({"role": "user", "content": message})
    try:
        resp = requests.post(endpoint + "/chat/completions", headers=headers, json={
            "model": model,
            "messages": prompt_messages,
        }, timeout=30)
        data = resp.json()
        content = (
            (data.get("choices") or [{}])[0]
            .get("message", {})
            .get("content", "")
        )
        obj = json.loads(content) if content else {"intent": "unknown", "response": "I'm not sure how to help with that."}
        return obj
    except Exception as e:
        return {"intent": "help", "response": "Sorry, there was a problem processing your request. I can help you configure Aqua Maker or show you examples."}

# Instantiate with fetch env provided
if __name__ == "__main__":
    class PrintBackAgent(MakerAgent):
        def send_message(self, recipient, data):
            print(f"\n--- Message to {recipient} ---")
            print(json.dumps(data, indent=2))

    agent = PrintBackAgent(
        os.getenv('LLM_API_ENDPOINT'),
        os.getenv('LLM_API_KEY'),
        os.getenv('LLM_MODEL'),
    )

    print("--- Manual Test Mode ---")
    while True:
        user = input("Type a message for the agent (or 'exit' to quit): ")
        if user.lower() == "exit":
            break
        agent.handle_message(user, "manual_tester")
