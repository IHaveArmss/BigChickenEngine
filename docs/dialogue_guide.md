# Dialogue System Guide

## Quick Start

To add dialogue to an NPC, create a script with an `on_interact()` method that returns the dialogue data.

---

## Basic Dialogue (No State)

```python
class MyNpc:
    def on_interact(self):
        return [
            {"speaker": "Guard", "text": "Hello traveler!"},
            {"speaker": "Guard", "text": "What brings you here?", "choices": [
                {"text": "I'm looking for adventure.", "next": 2},
                {"text": "Just passing through.", "next": 3},
            ]},
            {"speaker": "Guard", "text": "Adventure awaits in the forest!"},
            {"speaker": "Guard", "text": "Safe travels!"},
        ]
```

**How it works:**
- List of nodes with integer indices
- `"next": 2` jumps to index 2
- `"next": -1` or end of list = exit

---

## Stateful Dialogue (Remembers Choices)

For the system to remember choices, use the new dict format:

```python
class MyNpc:
    def on_interact(self):
        return {
            "start_node": "greeting",
            "nodes": {
                "greeting": {
                    "speaker": "Guard",
                    "text": "Hello!",
                    "choices": [
                        {"text": "Who are you?", "next": "identity", "set_flag": {"met_guard": True}},
                        {"text": "Goodbye.", "next": "exit"},
                    ]
                },
                "identity": {
                    "speaker": "Guard",
                    "text": "I am the village guard.",
                    "next": "exit",
                },
                "exit": {"text": ""}  # Empty ends dialogue
            }
        }
```

---

## Features

### 1. Set Flag (Remembers Choice)

```python
{"text": "Yes I met the king", "next": "thank_you", "set_flag": {"met_king": True}}
```

This sets `engine.global_flags["met_king"] = True`.

### 2. Dynamic Start Node

```python
def on_interact(self):
    # Start at different node based on state
    start = "greeting_met" if self.engine.global_flags.get("met_guard") else "greeting_new"
    
    return {
        "start_node": start,
        "nodes": {...}
    }
```

### 3. Conditional Choices (Requires)

```python
{
    "text": "Tell me the secret",
    "next": "secret",
    "requires": {"found_secret": True}  # Only shows if flag is True
}
```

The choice only appears if `global_flags["found_secret"]` is `True`.

### 4. Custom Actions

```python
# In dialogue
{"text": "Take this reward", "next": "exit", "action": "give_gold"}

# In script
def on_dialogue_action(self, action_name):
    if action_name == "give_gold":
        self.engine.global_flags["gold"] += 100
```

---

## Controls

| Key | Action |
|-----|--------|
| `E` | Start dialogue / Continue |
| `1-4` | Select choice |
| `E` (while choices shown) | Does nothing (must pick choice first) |
| `Esc` | Exit dialogue |

---

## Full Example

```python
class TraderNpc:
    def on_interact(self):
        # Different greeting based on previous interaction
        start = "met_before" if self.engine.global_flags.get("talked_to_trader") else "first_meeting"
        
        return {
            "start_node": start,
            "nodes": {
                "first_meeting": {
                    "speaker": "Trader",
                    "text": "Welcome! Looking to buy or sell?",
                    "choices": [
                        {"text": "Buy something", "next": "shop", "set_flag": {"talked_to_trader": True}},
                        {"text": "Just looking", "next": "exit"},
                    ]
                },
                "met_before": {
                    "speaker": "Trader",
                    "text": "Welcome back! Anything new to trade?",
                    "choices": [
                        {
                            "text": "I found a rare gem!",
                            "next": "sell_gem",
                            "requires": {"has_gem": True}  # Only if player has gem
                        },
                        {"text": "Just browsing", "next": "exit"},
                    ]
                },
                "shop": {
                    "speaker": "Trader",
                    "text": "Here's my inventory...",
                    "next": "exit",
                },
                "sell_gem": {
                    "speaker": "Trader",
                    "text": "Wow! I'll pay 100 gold!",
                    "action": "sell_gem",  # Triggers script action
                    "next": "exit",
                },
                "exit": {"text": ""}
            }
        }
    
    def on_dialogue_action(self, action_name):
        if action_name == "sell_gem":
            self.engine.global_flags["gold"] += 100
            self.engine.global_flags["has_gem"] = False
```

---

## Summary

| Feature | Syntax |
|---------|--------|
| Set flag | `"set_flag": {"flag_name": True}` |
| Conditional choice | `"requires": {"flag_name": True}` |
| Custom action | `"action": "action_name"` |
| Dynamic start | Use `if` in `on_interact()` to set `start_node` |
| Exit dialogue | `{"text": ""}` or `"next": "exit"` |