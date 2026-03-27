"""AudioManager — play music and sound effects via pygame.mixer."""

import os
import pygame


class AudioManager:
    def __init__(self, sfx_channels=16):
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=1024)
        pygame.mixer.set_num_channels(sfx_channels)

        self._sfx_cache = {}
        self._sfx_volume = 1.0
        self._music_volume = 1.0

    # ------------------------------------------------------------------
    # Sound effects
    # ------------------------------------------------------------------

    def play_sfx(self, path, volume=None, loops=0):
        """Play a short sound effect. Caches the file after first load.
        Returns the pygame Channel or None if the file is missing."""
        path = os.path.abspath(path)
        sound = self._sfx_cache.get(path)
        if sound is None:
            if not os.path.exists(path):
                print(f"[Audio] WARNING: SFX not found: {path}")
                return None
            sound = pygame.mixer.Sound(path)
            self._sfx_cache[path] = sound

        vol = volume if volume is not None else self._sfx_volume
        sound.set_volume(vol)
        return sound.play(loops)

    def set_sfx_volume(self, volume):
        """Set the default volume for future SFX (0.0 – 1.0)."""
        self._sfx_volume = max(0.0, min(1.0, volume))

    # ------------------------------------------------------------------
    # Music (streamed, one track at a time)
    # ------------------------------------------------------------------

    def play_music(self, path, volume=None, loops=-1, fade_ms=0):
        """Stream background music. loops=-1 means infinite loop."""
        path = os.path.abspath(path)
        if not os.path.exists(path):
            print(f"[Audio] WARNING: Music not found: {path}")
            return
        pygame.mixer.music.load(path)
        pygame.mixer.music.set_volume(volume if volume is not None else self._music_volume)
        pygame.mixer.music.play(loops, fade_ms=fade_ms)

    def stop_music(self, fade_ms=0):
        if fade_ms > 0:
            pygame.mixer.music.fadeout(fade_ms)
        else:
            pygame.mixer.music.stop()

    def pause_music(self):
        pygame.mixer.music.pause()

    def resume_music(self):
        pygame.mixer.music.unpause()

    def set_music_volume(self, volume):
        self._music_volume = max(0.0, min(1.0, volume))
        pygame.mixer.music.set_volume(self._music_volume)

    def is_music_playing(self):
        return pygame.mixer.music.get_busy()

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def stop_all(self):
        """Stop all sounds and music."""
        pygame.mixer.stop()
        pygame.mixer.music.stop()

    def destroy(self):
        self.stop_all()
        self._sfx_cache.clear()
