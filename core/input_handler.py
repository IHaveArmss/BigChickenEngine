"""Input handler — processes pygame events and dispatches actions."""

import os
import pygame
from core.raycaster import screen_to_floor, pick_object, pick_object_from_screen
from core.scene_loader import save_scene, spawn_from_entry


class InputHandler:
    """Processes all keyboard and mouse events, dispatching to engine subsystems."""

    def __init__(self, engine):
        self.engine = engine

    def set_cursor_mode(self, cursor_on):
        """Toggle cursor grab/visibility."""
        self.engine.cursor_mode = cursor_on
        pygame.event.set_grab(not cursor_on)
        pygame.mouse.set_visible(cursor_on)
        if not cursor_on:
            pygame.mouse.set_pos(
                self.engine.win_size[0] // 2,
                self.engine.win_size[1] // 2,
            )

    def process_events(self):
        """Process all pending pygame events."""
        eng = self.engine
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                eng._quit()
            elif event.type in (pygame.VIDEORESIZE, getattr(pygame, "WINDOWSIZECHANGED", None)):
                # Keep engine/UI sizes in sync with the OS window size.
                # For OpenGL, pygame may require resetting the display mode.
                try:
                    size = getattr(event, "size", None) or (event.w, event.h)
                except Exception:
                    size = None
                if size and size[0] > 0 and size[1] > 0:
                    eng.on_resize(size)
            
            elif event.type == pygame.WINDOWFOCUSGAINED:
                if not eng.cursor_mode:
                    pygame.event.set_grab(True)
            
            elif event.type == pygame.WINDOWFOCUSLOST:
                pygame.event.set_grab(False)

            elif event.type == pygame.KEYDOWN:
                if eng.editor_ui.has_active_input():
                    eng.editor_ui.handle_event(event, pygame.mouse.get_pos())
                    continue
                if eng.scene_hierarchy.has_active_input():
                    eng.scene_hierarchy.handle_event(
                        event, pygame.mouse.get_pos(),
                        eng.scene_objects, eng.selected_index
                    )
                    continue
                if eng.script_manager.dispatch_key_down(event.key, getattr(event, 'mod', 0)):
                    continue
                self._handle_key_down(event)

            elif event.type == pygame.MOUSEBUTTONDOWN:
                self._handle_mouse_down(event)

            elif event.type == pygame.MOUSEMOTION:
                if not eng.cursor_mode and not eng.dialogue.active and eng.input_enabled:
                    dx, dy = event.rel
                    eng.active_camera.process_mouse(dx, dy)

    # ------------------------------------------------------------------

    def _handle_key_down(self, event):
        eng = self.engine

        # Dialogue input takes priority during active dialogue
        if eng.dialogue.active:
            if event.key == pygame.K_UP:
                eng.dialogue.move_selection(-1)
            elif event.key == pygame.K_DOWN:
                eng.dialogue.move_selection(1)
            elif event.key == pygame.K_e:
                if eng.dialogue._choices is None:
                    eng.dialogue.advance()
            elif event.key == pygame.K_RETURN:
                if eng.dialogue._choices is not None:
                    eng.dialogue.confirm_selection()
                else:
                    eng.dialogue.advance()
            elif event.key == pygame.K_1:
                eng.dialogue.select_choice(0)
            elif event.key == pygame.K_2:
                eng.dialogue.select_choice(1)
            elif event.key == pygame.K_3:
                eng.dialogue.select_choice(2)
            elif event.key == pygame.K_4:
                eng.dialogue.select_choice(3)
            elif event.key == pygame.K_ESCAPE:
                eng.dialogue._begin_end()
            return  # Block all other input during dialogue

        if event.key == pygame.K_ESCAPE:
            if eng.cursor_mode:
                self.set_cursor_mode(False)
                eng.editor_ui.placement_mode = None
            else:
                eng._quit()

        elif event.key == pygame.K_F1:
            eng.toggle_dev_mode()
            eng.hud.dev_mode = eng.dev_mode
            eng.editor_ui.visible = eng.dev_mode
            if eng.dev_mode:
                print(f"\n[DevMode] ON — cursor mode")
            else:
                eng.editor_ui.visible = False
                eng.editor_ui.placement_mode = None
                print("[DevMode] OFF")

        elif event.key == pygame.K_F2:
            self.set_cursor_mode(not eng.cursor_mode)
            if not eng.cursor_mode:
                eng.editor_ui.placement_mode = None

        elif event.key == pygame.K_F3 and eng.dev_mode:
            eng.scene_hierarchy.toggle()

        elif event.key == pygame.K_h:
            eng.hud.toggle_controls()

        elif event.key == pygame.K_TAB and eng.dev_mode:
            eng.dev_tools.print_scene_info(
                eng.current_scene_file, eng.scene_objects, eng.selected_index
            )
            save_scene(eng.current_scene_file, eng.scene_objects,
                       settings=eng._build_scene_settings())

        elif event.key == pygame.K_s and (pygame.key.get_mods() & pygame.KMOD_CTRL):
            if eng.dev_mode:
                save_scene(eng.current_scene_file, eng.scene_objects, settings=eng._build_scene_settings())
        elif event.key == pygame.K_z and (pygame.key.get_mods() & pygame.KMOD_CTRL):
            if eng.dev_mode:
                eng.undo()
        elif event.key == pygame.K_y and (pygame.key.get_mods() & pygame.KMOD_CTRL):
            if eng.dev_mode:
                eng.redo()

        elif event.key == pygame.K_c and eng.dev_mode and not eng.cursor_mode:
            eng.selected_index = eng.dev_tools.spawn_in_front(
                eng.ctx, 'cube', eng.active_camera, eng.scene_objects,
                eng._rebuild_renderables, eng.editor_ui, eng.shader_cache,
            )

        elif event.key == pygame.K_e and not eng.dev_mode and eng.input_enabled:
            eng.interaction_manager.try_interact()

        elif event.key == pygame.K_DELETE and eng.dev_mode:
            eng.selected_index = eng.dev_tools.delete_selected(
                eng.scene_objects, eng.selected_index,
                eng._rebuild_renderables, eng.editor_ui,
            )

    def _handle_mouse_down(self, event):
        eng = self.engine

        if eng.cursor_mode:
            mouse_pos = pygame.mouse.get_pos()

            if eng.editor_ui.is_point_on_panel(mouse_pos):
                action = eng.editor_ui.handle_event(event, mouse_pos)
                if action:
                    if action['action'] == 'save_as':
                        eng._save_as(action['filename'])
                    elif action['action'] == 'save_current_scene':
                        save_scene(eng.current_scene_file, eng.scene_objects, settings=eng._build_scene_settings())
                        print(f"[DevMode] Scene saved: {eng.current_scene_file}")
                    elif action['action'] == 'load_scene':
                        raw = (action.get('scene') or '').strip().replace('\\', '/')
                        if not raw:
                            print("[DevMode] Scene load canceled: empty path")
                        else:
                            if raw in eng.list_scene_files():
                                scene_path = raw
                            else:
                                base = raw[:-5] if raw.endswith('.json') else raw
                                scene_path = os.path.join('scenes', f'{base}.json').replace('\\', '/')
                            if os.path.exists(scene_path):
                                eng.load_scene(scene_path)
                                eng.editor_ui.set_scene_context(eng.current_scene_file, eng.list_scene_files())
                                print(f"[DevMode] Loaded scene: {scene_path}")
                            else:
                                print(f"[DevMode] Scene not found: {scene_path}")
                    elif action['action'] == 'reload_scene':
                        eng.load_scene(eng.current_scene_file)
                        eng.editor_ui.set_scene_context(eng.current_scene_file, eng.list_scene_files())
                        print(f"[DevMode] Reloaded scene: {eng.current_scene_file}")
                    elif action['action'] == 'undo':
                        eng.undo()
                    elif action['action'] == 'redo':
                        eng.redo()
                    elif action['action'] == 'save_prefab_selected':
                        prefab_name = (action.get('prefab') or '').strip()
                        if not prefab_name:
                            print("[DevMode] Prefab save canceled: empty name")
                        elif 0 <= eng.selected_index < len(eng.scene_objects):
                            obj = eng.scene_objects[eng.selected_index]
                            eng.save_prefab(obj, prefab_name)
                            eng.editor_ui.set_prefab_context(eng.list_prefab_names())
                        else:
                            print("[DevMode] Prefab save failed: no selected object")
                    elif action['action'] == 'spawn_prefab':
                        prefab_name = (action.get('prefab') or '').strip()
                        if not prefab_name:
                            print("[DevMode] Prefab spawn canceled: empty name")
                        else:
                            obj = eng.spawn_prefab(prefab_name)
                            if obj is None:
                                print(f"[DevMode] Prefab spawn failed: {prefab_name}")
                            else:
                                print(f"[DevMode] Spawned prefab: {prefab_name}")
                    elif action['action'] == 'autosave_toggle':
                        eng.autosave_enabled = action['enabled']
                        eng.autosave_timer = 0.0
                        status = "ON" if eng.autosave_enabled else "OFF"
                        print(f"[DevMode] Autosave: {status}")
                    elif action['action'] == 'spawn_model':
                        model_path = action.get('model', '').strip()
                        if not model_path:
                            print("[DevMode] Model spawn canceled: empty path")
                        else:
                            eng.editor_ui.placement_mode = 'model'
                            eng.editor_ui._pending_model_path = model_path.replace('\\', '/')
                            print(f"[DevMode] Click to place model: {model_path}")
                    elif action['action'].startswith('anim_'):
                        eng.dev_tools.handle_anim_action(
                            action, eng.scene_objects, eng.selected_index, eng.editor_ui
                        )
                    elif action['action'] == 'scripts_apply':
                        if action.get('mode') == 'add':
                            eng.dev_tools.add_scripts(
                                eng.scene_objects, eng.selected_index, action.get('scripts', []), eng.editor_ui
                            )
                        elif action.get('mode') == 'remove':
                            eng.dev_tools.remove_scripts(
                                eng.scene_objects, eng.selected_index, action.get('scripts', []), eng.editor_ui
                            )
                    elif action['action'] == 'cutscene_add_point':
                        eng.cutscenes.add_waypoint()
                        eng.editor_ui.cutscene_waypoint_count = len(eng.cutscenes.waypoints)
                        print(f"[Cutscene] Added waypoint #{len(eng.cutscenes.waypoints)}")
                    elif action['action'] == 'cutscene_play':
                        eng.cutscenes.play()
                    elif action['action'] == 'cutscene_stop':
                        eng.cutscenes.stop()
                    elif action['action'] == 'cutscene_clear':
                        eng.cutscenes.clear()
                        eng.editor_ui.cutscene_waypoint_count = 0
                        print("[Cutscene] Cleared all waypoints")
                    elif action['action'] == 'cutscene_save':
                        name = (action.get('name') or '').strip()
                        if not name:
                            print("[Cutscene] Save canceled: empty name")
                        else:
                            eng.cutscenes.save(name)
                            eng.editor_ui.available_cutscenes = eng.cutscenes.list_cutscenes()
                    elif action['action'] == 'cutscene_load':
                        name = (action.get('name') or '').strip()
                        if name and name != "(no cutscenes)":
                            if eng.cutscenes.load(name):
                                eng.editor_ui.cutscene_waypoint_count = len(eng.cutscenes.waypoints)
                                eng.editor_ui.cutscene_can_player_move = eng.cutscenes.can_player_move
                                eng.editor_ui.cutscene_is_looping = eng.cutscenes.is_looping
                                eng.editor_ui.cutscene_speed_input.text = str(eng.cutscenes.playback_speed)
                    elif action['action'] == 'refresh_ui':
                        eng.editor_ui._current_obj_name = None
                    elif action['action'] == 'spawn_sprite':
                        sprite_path = (action.get('path') or '').strip()
                        sprite_name = (action.get('name') or 'sprite').strip()
                        billboard = action.get('billboard', True)
                        autocrop = action.get('autocrop', True)
                        if not sprite_path:
                            print("[DevMode] Sprite spawn canceled: empty path")
                        else:
                            # Store pending data for DevMode to read (kept for compatibility)
                            eng.editor_ui._pending_sprite_path = sprite_path.replace('\\', '/')
                            eng.editor_ui._pending_sprite_name = sprite_name
                            eng.editor_ui._pending_sprite_billboard = billboard
                            eng.editor_ui._pending_sprite_autocrop = autocrop
                            
                            # Spawn immediately in front!
                            new_idx = eng.dev_tools.spawn_in_front(
                                eng.ctx, 'sprite', eng.active_camera, 
                                eng.scene_objects, eng._rebuild_renderables, 
                                eng.editor_ui, shader_cache=eng.shader_cache, 
                                texture_loader=eng.texture_loader
                            )
                            if new_idx >= 0:
                                eng.selected_index = new_idx
                                print(f"[DevMode] Spawned sprite: {sprite_name}")

            elif eng.scene_hierarchy.is_point_on_panel(mouse_pos):
                new_idx = eng.scene_hierarchy.handle_event(
                    event, mouse_pos, eng.scene_objects, eng.selected_index
                )
                if new_idx != eng.selected_index:
                    eng.selected_index = new_idx
                    eng.editor_ui._current_obj_name = None
                    if new_idx >= 0:
                        print(f"[Hierarchy] Selected: '{eng.scene_objects[new_idx].name}'")
                    else:
                        print("[Hierarchy] Deselected")
            else:
                # Click in viewport
                if eng.editor_ui.placement_mode:
                    floor_hit = screen_to_floor(eng.active_camera, eng.win_size, *mouse_pos)
                    if floor_hit:
                        eng.selected_index = eng.dev_tools.spawn_at(
                            eng.ctx, eng.editor_ui.placement_mode, floor_hit,
                            eng.scene_objects, eng._rebuild_renderables, eng.editor_ui,
                            eng.shader_cache, eng.texture_loader,
                        )
                    else:
                        eng.selected_index = eng.dev_tools.spawn_in_front(
                            eng.ctx, eng.editor_ui.placement_mode, eng.active_camera,
                            eng.scene_objects, eng._rebuild_renderables, eng.editor_ui,
                            eng.shader_cache,
                        )
                    if eng.editor_ui.placement_mode != 'model':
                        eng.editor_ui.placement_mode = None
                elif eng.dev_mode:
                    idx = pick_object_from_screen(
                        eng.active_camera, eng.win_size, eng.scene_objects, *mouse_pos,
                        physics_system=eng.physics_system
                    )
                    if idx >= 0:
                        eng.selected_index = idx
                        eng.editor_ui._current_obj_name = None
                        obj = eng.scene_objects[idx]
                        print(f"[DevMode] Selected: '{obj.name}' (id={obj.id})")
                    elif eng.selected_index >= 0:
                        eng.selected_index = -1
                        eng.editor_ui._current_obj_name = None
                        print("[DevMode] Deselected")

        elif not eng.dev_mode and event.button == 1:
            eng.script_manager.dispatch_mouse_down(1)
        
        elif eng.dev_mode and event.button == 1:
            idx = pick_object(eng.active_camera, eng.scene_objects,
                             physics_system=eng.physics_system)
            if idx >= 0:
                eng.selected_index = idx
                eng.editor_ui._current_obj_name = None
                print(f"[DevMode] Selected: '{eng.scene_objects[idx].name}'")
            elif eng.selected_index >= 0:
                eng.selected_index = -1
                eng.editor_ui._current_obj_name = None
                print("[DevMode] Deselected")
