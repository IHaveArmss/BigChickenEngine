"""Test script for the AudioManager.

Attach this to any object. When Play Mode starts:
  - Background music plays (if assets/audio/music.ogg exists)
  - Press SPACE to play a sound effect (if assets/audio/sfx.wav exists)
  - Press M to toggle music pause/resume
  - Press UP/DOWN to adjust music volume

If the audio files don't exist, warnings are printed but nothing crashes.
"""

import pygame


class AudioTest:
    def start(self):
        self.audio = self.engine.audio
        self.music_paused = False
        self.music_volume = 0.7

        self.audio.set_music_volume(self.music_volume)
        self.audio.play_music("assets/audio/music.ogg", volume=self.music_volume)
        print("[AudioTest] Started. SPACE=SFX, M=pause/resume, UP/DOWN=volume")

    def update(self, dt):
        keys = pygame.key.get_pressed()

        if keys[pygame.K_SPACE]:
            self.audio.play_sfx("assets/audio/sfx.wav")

        if keys[pygame.K_m]:
            if not self.music_paused:
                self.audio.pause_music()
                self.music_paused = True
                print("[AudioTest] Music paused")
            else:
                self.audio.resume_music()
                self.music_paused = False
                print("[AudioTest] Music resumed")

        if keys[pygame.K_UP]:
            self.music_volume = min(1.0, self.music_volume + dt * 0.5)
            self.audio.set_music_volume(self.music_volume)
        if keys[pygame.K_DOWN]:
            self.music_volume = max(0.0, self.music_volume - dt * 0.5)
            self.audio.set_music_volume(self.music_volume)

    def stop(self):
        self.audio.stop_all()
        print("[AudioTest] Stopped.")
