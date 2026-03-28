import glm
import math

class LobbyNpc:
    """
    Lobby NPC with 'Look At Player' focus.
    """

    def start(self):
        self.entity.interactable = True
        self._has_spoken = False

    def on_interact(self):
        if self._has_spoken:
            self.engine.dialogue.talk_sounds = [
                "assets/sounds/talkingpizza1.mp3",
                "assets/sounds/talkingpizza2.mp3",
                "assets/sounds/talkingpizza3.mp3",
            ]
            return {
                "start_node": "repeat",
                "nodes": {
                    "repeat": {
                        "speaker": "Jane Juliet",
                        "text": "Well, the door is the other way....",
                        "next": "exit"
                    },
                    "exit": {
                        "text": ""
                    }
                }
            }
        
        self._has_spoken = True
        self.engine.dialogue.talk_sounds = [
            "assets/sounds/talkingpizza1.mp3",
            "assets/sounds/talkingpizza2.mp3",
            "assets/sounds/talkingpizza3.mp3",
        ]
        player = self.engine.interaction_manager._get_player()
        target_pos = player.position if player else self.engine.active_camera.position
        
        diff = target_pos - self.entity.position
        if glm.length(glm.vec3(diff.x, 0, diff.z)) > 0.01:
            angle_rad = math.atan2(-diff.x, -diff.z)
            self.entity.rotation_euler.y = math.degrees(angle_rad)
            self.entity._physics_dirty = True
            
        return {
            "start_node": "line_0",
            "nodes": {
                "line_0": {
                    "speaker": "Jane Juliet",
                    "text": "Welcome to Evil Inc. How can i help you today?",
                    "next": "choices1"
                },
                "response_a": {
                    "speaker": "Jane Juliet",
                    "text": "You could have gotten here sooner, I was getting hungry.",
                    "next": "exit"
                },
                "response_b": {
                    "speaker": "Jane Juliet",
                    "text": "Yeah really, we are the worst company in the world! We do evil things and we don't care about the consequences!",
                    "next": "line_1"
                },
                "choices1": {
                    "speaker": "Jane Juliet",
                    "text": "Choose your answer:",
                    "choices": [
                        {
                            "text": "Got a pizza delivery for you.",
                            "next": "response_a"
                        },
                        {
                            "text": "Really Evil Inc....",
                            "next": "response_b"
                        }
                    ]
                },
                "line_1": {
                    "speaker": "Jane Juliet",
                    "text": "Why you are you here anyway?",
                    "next": "choices2"
                },
                "choices2": {
                    "speaker": "Jane Juliet",
                    "text": "Choose your answer:",
                    "choices": [
                        {
                            "text": "I have a pizza delivery for you!",
                            "next": "response_a"
                        }
                    ]
                },
                "exit": {
                    "text": ""
                }
            }
        }
