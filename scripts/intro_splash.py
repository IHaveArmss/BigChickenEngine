import os

class IntroSplash:
    """
    Shows a fullscreen image for 3 seconds when the scene starts.
    Attach this to any object in the scene.
    """
    def start(self):
        # Default path
        self.image_path = "assets/textures/splash.png"
        self.duration = 3.0
        
        # Trigger the engine's new overlay system
        if os.path.exists(self.image_path):
            self.engine.show_image_overlay(self.image_path, self.duration)
        else:
            print(f"[IntroSplash] Skipping: {self.image_path} not found.")

    def update(self, dt):
        pass
