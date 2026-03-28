"""ScriptManager — Dynamically loads, unloads, and executes Python scripts attached to scene objects."""

import importlib.util
import traceback
import sys
import os
from core.utils import normalize_script_names


class ScriptManager:
    def __init__(self):
        self.active_scripts = []
        self._loaded_module_names = []

    def load_scripts(self, engine, scene_objects):
        """Finds all scripts on objects, loads them, and runs their start() methods."""
        self.stop_all()

        print("[ScriptManager] Loading scripts...")
        for obj in scene_objects:
            if not hasattr(obj, 'scripts') or not obj.scripts:
                continue

            script_names = normalize_script_names(obj.scripts)
            obj.scripts = script_names
            for script_name in script_names:
                script_path = script_name
                if not script_path.endswith('.py'):
                    script_path += '.py'

                normalized_path = script_path.replace('\\', '/')
                if not normalized_path.startswith('scripts/'):
                    script_path = os.path.join('scripts', script_path)

                script_path = os.path.abspath(script_path)

                if not os.path.exists(script_path):
                    print(f"[ScriptManager] WARNING: Script not found: {script_path}")
                    continue

                module_name = os.path.splitext(os.path.basename(script_path))[0]

                # Evict stale module so reimport picks up edits
                sys.modules.pop(module_name, None)

                try:
                    spec = importlib.util.spec_from_file_location(module_name, script_path)
                    if not spec or not spec.loader:
                        print(f"[ScriptManager] WARNING: Could not create spec for {script_path}")
                        continue

                    module = importlib.util.module_from_spec(spec)
                    sys.modules[module_name] = module
                    spec.loader.exec_module(module)
                    self._loaded_module_names.append(module_name)
                except Exception:
                    print(f"[ScriptManager] ERROR loading {script_path}:\n{traceback.format_exc()}")
                    continue

                class_name = ''.join(word.capitalize() for word in module_name.split('_'))

                script_class = getattr(module, class_name, None)
                if not script_class:
                    script_class = getattr(module, 'Script', None)

                if script_class:
                    instance = script_class()
                    instance.engine = engine
                    instance.entity = obj

                    self.active_scripts.append(instance)
                    print(f"[ScriptManager] Loaded {class_name} on {obj.name}")

                    if hasattr(instance, 'start'):
                        try:
                            instance.start()
                        except Exception:
                            print(f"[ScriptManager] ERROR in {class_name}.start():\n{traceback.format_exc()}")
                else:
                    print(f"[ScriptManager] WARNING: No valid class found in {script_path}. "
                          f"Expected '{class_name}' or 'Script'.")

    def update_all(self, dt):
        """Calls the update method on all loaded scripts. Errors are logged, not propagated."""
        for script in self.active_scripts:
            if hasattr(script, 'update'):
                try:
                    script.update(dt)
                except Exception:
                    name = type(script).__name__
                    print(f"[ScriptManager] ERROR in {name}.update():\n{traceback.format_exc()}")

    def fixed_update_all(self, fixed_dt):
        """Calls fixed_update on all scripts that define it (once per physics substep)."""
        for script in self.active_scripts:
            if hasattr(script, 'fixed_update'):
                try:
                    script.fixed_update(fixed_dt)
                except Exception:
                    name = type(script).__name__
                    print(f"[ScriptManager] ERROR in {name}.fixed_update():\n{traceback.format_exc()}")

    def dispatch_collisions(self, collisions):
        """Notify scripts about collisions detected this frame.
        collisions: list of (obj_a, obj_b, contact_point, normal, impulse)."""
        from core.physics_system import CollisionInfo
        entity_to_scripts = {}
        for script in self.active_scripts:
            if hasattr(script, 'on_collision'):
                entity_to_scripts.setdefault(id(script.entity), []).append(script)

        if not entity_to_scripts:
            return

        for obj_a, obj_b, point, normal, impulse in collisions:
            for script in entity_to_scripts.get(id(obj_a), ()):
                try:
                    script.on_collision(CollisionInfo(obj_b, point, normal, impulse))
                except Exception:
                    name = type(script).__name__
                    print(f"[ScriptManager] ERROR in {name}.on_collision():\n{traceback.format_exc()}")
            for script in entity_to_scripts.get(id(obj_b), ()):
                try:
                    script.on_collision(CollisionInfo(obj_a, point, -normal, impulse))
                except Exception:
                    name = type(script).__name__
                    print(f"[ScriptManager] ERROR in {name}.on_collision():\n{traceback.format_exc()}")

    def dispatch_interact(self, entity):
        """Call on_interact() on all scripts attached to entity.
        Returns the first non-None return value (dialogue data) if any."""
        for script in self.active_scripts:
            if script.entity is entity and hasattr(script, 'on_interact'):
                try:
                    result = script.on_interact()
                    if result is not None:
                        return result
                except Exception:
                    name = type(script).__name__
                    print(f"[ScriptManager] ERROR in {name}.on_interact():\n{traceback.format_exc()}")
        return None

    def dispatch_choice(self, entity, choice_index):
        """Call select_choice() on all scripts attached to entity when player makes a choice."""
        for script in self.active_scripts:
            if script.entity is entity and hasattr(script, 'select_choice'):
                try:
                    script.select_choice(choice_index)
                except Exception:
                    name = type(script).__name__
                    print(f"[ScriptManager] ERROR in {name}.select_choice():\n{traceback.format_exc()}")

    def dispatch_dialogue_action(self, entity, action_name):
        """Call on_dialogue_action() on all scripts attached to entity."""
        for script in self.active_scripts:
            if script.entity is entity and hasattr(script, 'on_dialogue_action'):
                try:
                    script.on_dialogue_action(action_name)
                except Exception:
                    name = type(script).__name__
                    print(f"[ScriptManager] ERROR in {name}.on_dialogue_action():\n{traceback.format_exc()}")

    def dispatch_mouse_down(self, button):
        """Notify all scripts about a mouse down event."""
        for script in self.active_scripts:
            if hasattr(script, 'on_mouse_down'):
                try:
                    script.on_mouse_down(button)
                except Exception:
                    name = type(script).__name__
                    print(f"[ScriptManager] ERROR in {name}.on_mouse_down():\n{traceback.format_exc()}")

    def stop_all(self):
        """Calls stop() on each script, then clears and cleans up loaded modules."""
        if self.active_scripts:
            print("[ScriptManager] Stopping and unloading scripts.")
        for script in self.active_scripts:
            if hasattr(script, 'stop'):
                try:
                    script.stop()
                except Exception:
                    name = type(script).__name__
                    print(f"[ScriptManager] ERROR in {name}.stop():\n{traceback.format_exc()}")
        self.active_scripts.clear()

        for mod_name in self._loaded_module_names:
            sys.modules.pop(mod_name, None)
        self._loaded_module_names.clear()
