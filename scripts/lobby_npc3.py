import glm
import math

class LobbyNpc3:
    """
    Lobby NPC with 'Look At Player' focus.
    """

    def start(self):
        self.entity.interactable = True
        self._has_spoken = False
        self._task_updated = False

    def update(self, dt):
        # Trigger task update after the first conversation ends
        if self._has_spoken and not self.engine.dialogue.active and not self._task_updated:
            self.engine.hud.set_task("The Bo$$", "Go to the top floor")
            self._task_updated = True

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
                        "text": "Good luck.... I guess.",
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
                    "text": "Welcome to Evil Inc. Leave while you still can!",
                    "next": "choices1"
                },
                "response_b": {
                    "speaker": "Jane Juliet",
                    "text": "Who are you anyway?",
                    "next": "choices2"
                },
                "response_c": {
                    "speaker": "Jane Juliet",
                    "text": "On the top floor...",
                    "next": "exit"
                },
                "choices1": {
                    "speaker": "Jane Juliet",
                    "text": "Choose your answer:",
                    "choices": [
                        {
                            "text": "Haven't we met before?",
                            "next": "response_b"
                        },
                        {
                            "text": "You better leave.",
                            "next": "response_b"
                        }
                    ]
                },
                "choices2": {
                    "speaker": "Jane Juliet",
                    "text": "Choose your answer:",
                    "choices": [
                        {
                            "text": "I'm here for your boss, where is he?",
                            "next": "response_c"
                        }
                    ]
                },
                "exit": {
                    "text": ""
                }
            }
        }
