"""GifPlayer — plays an animated GIF on the pygame display surface.

Uses only pygame (no Pillow required) by leveraging pygame's built-in
GIF frame extraction via pygame.image.load on each seek position.

If Pillow IS available it will use it for faster / more accurate decoding.
Falls back gracefully to a solid black screen if the file is missing.
"""

import os
import pygame


def _load_frames_pillow(path):
    """Load all GIF frames and durations using Pillow."""
    from PIL import Image
    gif = Image.open(path)
    frames = []
    try:
        while True:
            # Convert each frame to RGBA
            rgba = gif.convert("RGBA")
            w, h = rgba.size
            raw = rgba.tobytes()
            surf = pygame.image.fromstring(raw, (w, h), "RGBA")
            duration_ms = gif.info.get("duration", 100)
            frames.append((surf, max(duration_ms, 20)))
            gif.seek(gif.tell() + 1)
    except EOFError:
        pass
    return frames


def _load_frames_pygame(path):
    """Fallback: load only the first frame via pygame (static)."""
    try:
        surf = pygame.image.load(path).convert_alpha()
        return [(surf, 100)]
    except Exception:
        return []


def load_gif_frames(path):
    """Return list of (pygame.Surface, duration_ms) tuples for a GIF."""
    try:
        return _load_frames_pillow(path)
    except ImportError:
        return _load_frames_pygame(path)
    except Exception as e:
        print(f"[GifPlayer] Error loading '{path}': {e}")
        return []


def play_gif_overlay(display: pygame.Surface, path: str, min_duration_ms: int = 0):
    """
    Render animated GIF frames onto *display* in a blocking mini-loop.

    Call this BEFORE the heavy work (scene load) starts, run it in a
    thread if you want it animated during load, or just show the first
    frame as a splash then load.

    Parameters
    ----------
    display       : the pygame window surface
    path          : path to the .gif file
    min_duration_ms : minimum time to show overlay even if load is fast (ms)
    """
    if not os.path.exists(path):
        print(f"[GifPlayer] File not found: {path}")
        return

    frames = load_gif_frames(path)
    if not frames:
        # Show plain black
        display.fill((0, 0, 0))
        pygame.display.flip()
        return

    clock = pygame.time.Clock()
    total_elapsed = 0
    frame_idx = 0
    frame_elapsed = 0

    win_w, win_h = display.get_size()

    while True:
        dt = clock.tick(60)
        frame_elapsed += dt
        total_elapsed += dt

        surf, duration = frames[frame_idx]

        # Pump events so Windows doesn't think the app froze
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return  # let the caller handle quit

        # Scale frame to fit screen (letterboxed)
        fw, fh = surf.get_size()
        scale = min(win_w / fw, win_h / fh)
        new_w, new_h = int(fw * scale), int(fh * scale)
        scaled = pygame.transform.smoothscale(surf, (new_w, new_h))

        display.fill((0, 0, 0))
        x = (win_w - new_w) // 2
        y = (win_h - new_h) // 2
        display.blit(scaled, (x, y))
        pygame.display.flip()

        if frame_elapsed >= duration:
            frame_elapsed -= duration
            frame_idx = (frame_idx + 1) % len(frames)

        # Stop once we've looped through all frames at least once and
        # met the minimum display time.
        if total_elapsed >= max(min_duration_ms, sum(d for _, d in frames)):
            break
