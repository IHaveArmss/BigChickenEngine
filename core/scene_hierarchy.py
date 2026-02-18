"""Scene Hierarchy — left-side toggleable panel showing objects in folders."""

import pygame


# ── Style ─────────────────────────────────────────────────────────────
BG_COLOR = (20, 20, 30, 230)
PANEL_BORDER = (0, 200, 120, 200)
SECTION_COLOR = (0, 200, 120, 255)
LABEL_COLOR = (180, 180, 180)
ITEM_COLOR = (200, 200, 200)
ITEM_SELECTED = (100, 255, 150)
FOLDER_COLOR = (255, 200, 80)
HOVER_BG = (40, 40, 60, 150)
SELECTED_BG = (30, 80, 50, 180)
BUTTON_BG = (40, 40, 60)
BUTTON_HOVER = (60, 60, 90)
BUTTON_TEXT = (220, 220, 220)

PANEL_WIDTH = 260
PANEL_PADDING = 10
ROW_HEIGHT = 24
FOLDER_ROW_H = 28
ICON_SIZE = 14
INDENT = 20


class SceneHierarchy:
    """Left-side panel listing scene objects grouped into folders."""

    def __init__(self, win_size):
        self.win_size = win_size
        self.visible = False

        pygame.font.init()
        self.font = pygame.font.SysFont('Consolas', 14)
        self.font_bold = pygame.font.SysFont('Consolas', 14, bold=True)
        self.font_section = pygame.font.SysFont('Consolas', 16, bold=True)

        # Panel position (left side)
        self.panel_x = 10
        self.panel_y = 10

        # Folder tree structure
        # { folder_name: { 'open': True, 'order': 0 } }
        self.folders = {'Scene': {'open': True, 'order': 0}}
        self._next_order = 1

        # Scroll
        self.scroll_y = 0
        self.max_scroll = 0

        # State
        self._hovered_item = None  # (type, key) e.g. ('folder', 'Scene') or ('object', 3)
        self._row_rects = []  # [(rect, type, key), ...]

        # Add folder input
        self._adding_folder = False
        self._new_folder_text = ''

        # Move-to dropdown
        self.move_dropdown_open = False
        self.move_dropdown_rects = []

        # Button/hit rects (filled during draw)
        self._add_folder_btn_rect = pygame.Rect(0, 0, 0, 0)
        self._delete_btn_rects = []  # [(rect, folder_name), ...]
        self._export_btn_rects = []  # [(rect, folder_name), ...]

        # Pending export request (polled by engine)
        self._pending_export = None  # folder name or None

    def toggle(self):
        self.visible = not self.visible

    def _get_sorted_folders(self):
        return sorted(self.folders.keys(), key=lambda f: self.folders[f]['order'])

    def ensure_folder(self, name):
        if name not in self.folders:
            self.folders[name] = {'open': True, 'order': self._next_order}
            self._next_order += 1

    # ------------------------------------------------------------------
    # Hit testing
    # ------------------------------------------------------------------

    def is_point_on_panel(self, pos):
        if not self.visible:
            return False
        panel_h = self.win_size[1] - 20
        panel_rect = pygame.Rect(self.panel_x, self.panel_y,
                                 PANEL_WIDTH, panel_h)
        return panel_rect.collidepoint(pos)

    # ------------------------------------------------------------------
    # Event handling
    # ------------------------------------------------------------------

    def handle_event(self, event, mouse_pos, scene_objects, selected_index):
        """Handle click. Returns new selected_index or current one."""
        if not self.visible:
            return selected_index

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Check add folder button
            if self._add_folder_btn_rect.collidepoint(mouse_pos):
                self._adding_folder = True
                self._new_folder_text = ''
                return selected_index

            # Check export buttons
            for rect, folder_name in self._export_btn_rects:
                if rect.collidepoint(mouse_pos):
                    self._pending_export = folder_name
                    return selected_index

            # Check delete folder buttons
            for rect, folder_name in self._delete_btn_rects:
                if rect.collidepoint(mouse_pos):
                    self._delete_folder(folder_name, scene_objects)
                    return selected_index

            # Check rows
            for rect, item_type, key in self._row_rects:
                if rect.collidepoint(mouse_pos):
                    if item_type == 'folder':
                        self.folders[key]['open'] = not self.folders[key]['open']
                    elif item_type == 'object':
                        return key  # key is the index in scene_objects
                    return selected_index

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 4:
            # Scroll up
            self.scroll_y = max(0, self.scroll_y - ROW_HEIGHT)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 5:
            # Scroll down
            self.scroll_y = min(self.max_scroll, self.scroll_y + ROW_HEIGHT)

        elif event.type == pygame.KEYDOWN and self._adding_folder:
            if event.key == pygame.K_RETURN:
                name = self._new_folder_text.strip()
                if name and name not in self.folders:
                    self.ensure_folder(name)
                self._adding_folder = False
            elif event.key == pygame.K_ESCAPE:
                self._adding_folder = False
            elif event.key == pygame.K_BACKSPACE:
                self._new_folder_text = self._new_folder_text[:-1]
            elif event.unicode and event.unicode.isprintable():
                self._new_folder_text += event.unicode

        return selected_index

    def has_active_input(self):
        return self._adding_folder

    def pop_export_request(self):
        """Return and clear the pending export folder name, if any."""
        req = self._pending_export
        self._pending_export = None
        return req

    def _delete_folder(self, folder_name, scene_objects):
        """Delete a folder, moving its objects back to 'Scene'."""
        if folder_name == 'Scene':
            return  # Can't delete the default folder
        for obj in scene_objects:
            if getattr(obj, 'folder', 'Scene') == folder_name:
                obj.folder = 'Scene'
        if folder_name in self.folders:
            del self.folders[folder_name]

    def update(self, mouse_pos, scene_objects):
        if not self.visible:
            return
        # Update hover
        self._hovered_item = None
        for rect, item_type, key in self._row_rects:
            if rect.collidepoint(mouse_pos):
                self._hovered_item = (item_type, key)
                break
        # Ensure all object folders exist
        for obj in scene_objects:
            self.ensure_folder(getattr(obj, 'folder', 'Scene'))

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------

    def draw(self, surface, scene_objects, selected_index):
        if not self.visible:
            return

        panel_h = self.win_size[1] - 20
        panel_rect = pygame.Rect(self.panel_x, self.panel_y, PANEL_WIDTH, panel_h)

        # Background
        bg = pygame.Surface((PANEL_WIDTH, panel_h), pygame.SRCALPHA)
        bg.fill(BG_COLOR)
        surface.blit(bg, (self.panel_x, self.panel_y))
        pygame.draw.rect(surface, PANEL_BORDER, panel_rect, 2, border_radius=6)

        # Clip region for scrollable content
        clip_rect = pygame.Rect(self.panel_x + 2, self.panel_y + 2,
                                PANEL_WIDTH - 4, panel_h - 4)
        old_clip = surface.get_clip()
        surface.set_clip(clip_rect)

        bx = self.panel_x + PANEL_PADDING
        bw = PANEL_WIDTH - PANEL_PADDING * 2
        y = self.panel_y + PANEL_PADDING - self.scroll_y

        # Title
        title_surf = self.font_section.render("HIERARCHY", True, SECTION_COLOR[:3])
        surface.blit(title_surf, (bx, y))
        y += 26

        # Rebuild row rects
        self._row_rects = []
        self._delete_btn_rects = []
        self._export_btn_rects = []

        # Group objects by folder
        sorted_folders = self._get_sorted_folders()
        folder_contents = {f: [] for f in sorted_folders}
        for i, obj in enumerate(scene_objects):
            folder = getattr(obj, 'folder', 'Scene')
            if folder not in folder_contents:
                folder_contents[folder] = []
            folder_contents[folder].append((i, obj))

        for folder_name in sorted_folders:
            is_open = self.folders[folder_name]['open']

            # Folder row
            row_rect = pygame.Rect(bx, y, bw, FOLDER_ROW_H)
            hovered = (self._hovered_item == ('folder', folder_name))
            if hovered:
                pygame.draw.rect(surface, HOVER_BG, row_rect, border_radius=3)

            # Arrow icon
            arrow = "▼" if is_open else "▶"
            arrow_surf = self.font_bold.render(arrow, True, FOLDER_COLOR)
            surface.blit(arrow_surf, (bx + 4, y + 5))

            # Folder name
            name_surf = self.font_bold.render(folder_name, True, FOLDER_COLOR)
            surface.blit(name_surf, (bx + 20, y + 5))

            # Object count
            count = len(folder_contents.get(folder_name, []))
            count_surf = self.font.render(f"({count})", True, (100, 100, 120))
            surface.blit(count_surf, (bx + 22 + name_surf.get_width(), y + 6))

            self._row_rects.append((row_rect, 'folder', folder_name))

            # Export button (↑) — for all folders
            exp_x = bx + bw - 44
            exp_rect = pygame.Rect(exp_x, y + 3, 20, 20)
            exp_hovered = exp_rect.collidepoint(pygame.mouse.get_pos())
            exp_color = (100, 255, 150) if exp_hovered else (60, 140, 80)
            exp_surf = self.font_bold.render("\u2191", True, exp_color)
            surface.blit(exp_surf, (exp_x + 4, y + 4))
            self._export_btn_rects.append((exp_rect, folder_name))

            # Delete button (✕) for non-default folders
            if folder_name != 'Scene':
                del_x = bx + bw - 22
                del_rect = pygame.Rect(del_x, y + 3, 20, 20)
                del_hovered = del_rect.collidepoint(pygame.mouse.get_pos())
                del_color = (255, 80, 80) if del_hovered else (140, 60, 60)
                del_surf = self.font_bold.render("\u2715", True, del_color)
                surface.blit(del_surf, (del_x + 3, y + 5))
                self._delete_btn_rects.append((del_rect, folder_name))

            y += FOLDER_ROW_H

            # Children
            if is_open:
                for obj_idx, obj in folder_contents.get(folder_name, []):
                    row_rect = pygame.Rect(bx + INDENT, y, bw - INDENT, ROW_HEIGHT)

                    is_selected = (obj_idx == selected_index)
                    hovered = (self._hovered_item == ('object', obj_idx))

                    if is_selected:
                        pygame.draw.rect(surface, SELECTED_BG, row_rect, border_radius=3)
                    elif hovered:
                        pygame.draw.rect(surface, HOVER_BG, row_rect, border_radius=3)

                    # Type icon
                    icon_x = bx + INDENT + 4
                    icon_y = y + (ROW_HEIGHT - ICON_SIZE) // 2
                    if obj.is_light:
                        icon_c = (255, 230, 100)
                    elif obj.format == 'cube':
                        icon_c = (100, 100, 255)
                    elif obj.format == 'triangle':
                        icon_c = (255, 100, 50)
                    else:
                        icon_c = (150, 150, 150)
                    pygame.draw.rect(surface, icon_c,
                                     (icon_x, icon_y, ICON_SIZE, ICON_SIZE),
                                     border_radius=2)

                    # Name
                    text_color = ITEM_SELECTED if is_selected else ITEM_COLOR
                    name_surf = self.font.render(obj.name, True, text_color)
                    surface.blit(name_surf, (icon_x + ICON_SIZE + 6, y + 4))

                    self._row_rects.append((row_rect, 'object', obj_idx))
                    y += ROW_HEIGHT

            y += 2  # gap between folders

        # "New Folder" button
        y += 4
        btn_rect = pygame.Rect(bx, y, bw, 26)
        self._add_folder_btn_rect = btn_rect
        btn_hovered = btn_rect.collidepoint(pygame.mouse.get_pos())
        btn_color = BUTTON_HOVER if btn_hovered else BUTTON_BG
        pygame.draw.rect(surface, btn_color, btn_rect, border_radius=4)
        pygame.draw.rect(surface, PANEL_BORDER[:3], btn_rect, 1, border_radius=4)
        btn_text = self.font.render("+ New Folder", True, BUTTON_TEXT)
        surface.blit(btn_text, (bx + (bw - btn_text.get_width()) // 2, y + 5))
        y += 34

        # New folder input (if active)
        if self._adding_folder:
            input_rect = pygame.Rect(bx, y, bw, 26)
            pygame.draw.rect(surface, (30, 30, 45), input_rect)
            pygame.draw.rect(surface, (0, 200, 120), input_rect, 2, border_radius=3)
            text_surf = self.font.render(self._new_folder_text + "│", True, (255, 255, 255))
            surface.blit(text_surf, (bx + 6, y + 5))
            hint = self.font.render("Enter to create, Esc to cancel", True, (100, 100, 120))
            surface.blit(hint, (bx, y + 30))
            y += 60

        # Track max scroll
        content_h = y + self.scroll_y - self.panel_y
        self.max_scroll = max(0, content_h - panel_h + 20)

        surface.set_clip(old_clip)
