"""Input handler — processes pygame events and dispatches actions."""

import pygame
from core.raycaster import screen_to_floor, pick_object, pick_object_from_screen
from core.scene_loader import save_scene


class InputHandler:
    """Processes all keyboard and mouse events, dispatching to engine subsystems."""

    def __init__(self, engine):
        self.engine = engine

    def set_cursor_mode(self, cursor_on):
        """Toggle cursor grab/visibility."""
        self.engine.cursor_mode = cursor_on
        pygame.event.set_grab(not cursor_on)
        pygame.mouse.set_visible(cursor_on)
        if cursor_on:
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
                self._handle_key_down(event)

            elif event.type == pygame.MOUSEBUTTONDOWN:
                self._handle_mouse_down(event)

            elif event.type == pygame.MOUSEMOTION:
                if not eng.cursor_mode:
                    dx, dy = event.rel
                    eng.camera.process_mouse(dx, dy)

    # ------------------------------------------------------------------

    def _handle_key_down(self, event):
        eng = self.engine

        if event.key == pygame.K_ESCAPE:
            if eng.cursor_mode:
                self.set_cursor_mode(False)
                eng.editor_ui.placement_mode = None
            else:
                eng._quit()

        elif event.key == pygame.K_F1:
            eng.dev_mode = not eng.dev_mode
            eng.hud.dev_mode = eng.dev_mode
            eng.editor_ui.visible = eng.dev_mode
            if eng.dev_mode:
                self.set_cursor_mode(True)
                print(f"\n[DevMode] ON — cursor mode")
            else:
                self.set_cursor_mode(False)
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
            save_scene(eng.current_scene_file, eng.scene_objects)

        elif event.key == pygame.K_s and (pygame.key.get_mods() & pygame.KMOD_CTRL):
            if eng.dev_mode:
                save_scene(eng.current_scene_file, eng.scene_objects)

        elif event.key == pygame.K_c and eng.dev_mode and not eng.cursor_mode:
            eng.selected_index = eng.dev_tools.spawn_in_front(
                eng.ctx, 'cube', eng.camera, eng.scene_objects,
                eng._rebuild_renderables, eng.editor_ui,
            )

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
                    elif action['action'] == 'autosave_toggle':
                        eng.autosave_enabled = action['enabled']
                        eng.autosave_timer = 0.0
                        status = "ON" if eng.autosave_enabled else "OFF"
                        print(f"[DevMode] Autosave: {status}")

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
                    floor_hit = screen_to_floor(eng.camera, eng.win_size, *mouse_pos)
                    if floor_hit:
                        eng.selected_index = eng.dev_tools.spawn_at(
                            eng.ctx, eng.editor_ui.placement_mode, floor_hit,
                            eng.scene_objects, eng._rebuild_renderables, eng.editor_ui,
                        )
                    else:
                        eng.selected_index = eng.dev_tools.spawn_in_front(
                            eng.ctx, eng.editor_ui.placement_mode, eng.camera,
                            eng.scene_objects, eng._rebuild_renderables, eng.editor_ui,
                        )
                    eng.editor_ui.placement_mode = None
                elif eng.dev_mode:
                    idx = pick_object_from_screen(
                        eng.camera, eng.win_size, eng.scene_objects, *mouse_pos
                    )
                    if idx >= 0:
                        eng.selected_index = idx
                        eng.editor_ui._current_obj_name = None
                        print(f"[DevMode] Selected: '{eng.scene_objects[idx].name}'")
                    elif eng.selected_index >= 0:
                        eng.selected_index = -1
                        eng.editor_ui._current_obj_name = None
                        print("[DevMode] Deselected")

        elif eng.dev_mode and event.button == 1:
            idx = pick_object(eng.camera, eng.scene_objects)
            if idx >= 0:
                eng.selected_index = idx
                eng.editor_ui._current_obj_name = None
                print(f"[DevMode] Selected: '{eng.scene_objects[idx].name}'")
            elif eng.selected_index >= 0:
                eng.selected_index = -1
                eng.editor_ui._current_obj_name = None
                print("[DevMode] Deselected")
