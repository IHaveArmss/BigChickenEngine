"""
Example NPC — simple dialogue demonstration.

Attach to any object with "interactable": true in the scene JSON.
Add "scripts": ["example_npc"] to the object entry.
"""


class ExampleNpc:
    def on_interact(self):
        return {
            "start_node": "greeting",
            "nodes": {
                "greeting": {
                    "speaker": "Cacalin",
                    "text": "Esti skibidi?",
                    "choices": [
                        {"text": "Who are you?", "next": "identity"},
                        {"text": "Nice to meet you!", "next": "friendly"},
                    ]
                },
                "identity": {
                    "speaker": "Cacalin",
                    "text": "I am Cacalin, guardian of this place.",
                    "next": "end",
                },
                "friendly": {
                    "speaker": "Cacalin",
                    "text": "Welcome, friend! Safe travels.",
                    "next": "end",
                },
                "end": {
                    "speaker": "Cacalin",
                    "text": "Come back anytime!",
                    "next": "exit",
                },
                "exit": {
                    "text": ""
                }
            }
        }