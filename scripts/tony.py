import glm
import math

class Tony:
    """
    Pizza shop guardian NPC with 'Look At Player' focus.
    """

    def start(self):
        self.entity.interactable = True
        self._has_spoken = False
        self._task_updated = False
        self._post_shot_task_set = False

    def update(self, dt):
        # 1. Trigger mission task after talking to Tony the first time
        if self._has_spoken and not self.engine.dialogue.active and not self._task_updated:
            if not self.engine.global_flags.get('thief_shot'):
                self.engine.hud.set_task("Anything for money!", "Deliver pizza to Evil Inc.")
                self._task_updated = True

        # 2. Trigger 'Leave' task after talking to Tony AFTER the thief is shot
        if self.engine.global_flags.get('thief_shot') and not self.engine.dialogue.active and not self._post_shot_task_set:
            # We want this to trigger only if we've ACTUALLY finished the post-shot conversation
            # A simple way is to check if the camera is NOT in dialogue mode anymore
            self.engine.hud.set_task("Leave", "Leave building")
            self._post_shot_task_set = True

    def on_interact(self):
        # NARRATIVE BRANCH: After the Thief is shot
        if self.engine.global_flags.get('thief_shot'):
            self.engine.dialogue.talk_sounds = [
                "assets/sounds/talkingpizza1.mp3",
                "assets/sounds/talkingpizza2.mp3",
                "assets/sounds/talkingpizza3.mp3",
            ]
            return {
                "start_node": "postBossPizza",
                "nodes": {
                    "postBossPizza": {
                        "speaker": "Tony Esprano",
                        "text": "Sorry buddy pizza's 6$ now, ever since that missing [PLACEHOLDER], the big guy put the whole city under martial law, until they find the killer.",
                        "next": "postBossPizzaChoices"
                    },
                    "postBossPizzaChoices": {
                        "speaker": "Tony Esprano",
                        "text": "...",
                        "choices": [
                            {"text": "Yea who would do such a thing...", "next": "postBossPizzaResponse"},
                            {"text": "Who would do such a thing?", "next": "postBossPizzaResponse"}
                        ]
                    },
                    "postBossPizzaResponse": {
                        "speaker": "Tony Esprano",
                        "text": "Yea buddy lifes been hard on us the prices skyrocketed and we have this curfew, i got interrogated the first week, i suggest you watch out.",
                        "next": "exit"
                    },
                    "exit": { "text": "" }
                }
            }

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
                        "speaker": "Tony Esprano",
                        "text": "Get moving, you lazy bastard!!",
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
                    "speaker": "Tony Esprano",
                    "text": "What's up small fella, would you like to order?",
                    "next": "choices1"
                },
                "response_a": {
                    "speaker": "Tony Esprano",
                    "text": "It's a bit expensive fella, gonna cost you around 3 bucks.",
                    "next": "expensiveChoices"
                },
                "response_b": {
                    "speaker": "Tony Esprano",
                    "text": "You're in luck, I need some help.",
                    "next": "line_1"
                },
                "expensiveChoices": {
                    "speaker": "Tony Esprano",
                    "text": "...",
                    "choices": [
                        { "text": "I can't pay", "next": "line_1" },
                        { "text": "Can I do something else?", "next": "line_1" }
                    ]
                },
                "choices1": {
                    "speaker": "Tony Esprano",
                    "text": "Choose your answer:",
                    "choices": [
                        {
                            "text": "Give me the cheapest thing you got!",
                            "next": "response_a"
                        },
                        {
                            "text": "Looking for something extra..",
                            "next": "response_b"
                        }
                    ]
                },
                "line_1": {
                    "speaker": "Tony Esprano",
                    "text": "Hey listen i have a job you have to deliver a box of pizza to an old friend of mine, a corpo head from Evil Inc. , head over there",
                    "next": "choices2"
                },
                "choices2": {
                    "speaker": "Tony Esprano",
                    "text": "Choose your answer:",
                    "choices": [
                        {
                            "text": "I guess I ain't got a choice...",
                            "next": "line_2"
                        },
                        {
                            "text": "Alright, for a free pizza of course!",
                            "next": "line_2"
                        }
                    ]
                },
                "line_2": {
                    "speaker": "Tony Esprano",
                    "text": "I'm counting on you!",
                    "next": "exit"
                },
                "exit": {
                    "text": ""
                }
            }
        }
