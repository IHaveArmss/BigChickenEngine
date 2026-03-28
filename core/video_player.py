import cv2
import pygame
import moderngl

class VideoPlayer:
    def __init__(self, ctx, shader_cache, filepath):
        self.ctx = ctx
        self.shader_cache = shader_cache
        self.filepath = filepath

        self.cap = cv2.VideoCapture(self.filepath)
        if not self.cap.isOpened():
            print(f"[VideoPlayer] Failed to open {self.filepath}")
            self.valid = False
            return
            
        self.valid = True
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        if self.fps <= 0:
            self.fps = 30.0
            
        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # Create a texture for the video frame. RGB format (3 components)
        self.texture = self.ctx.texture((self.width, self.height), 3)
        self.texture.filter = (moderngl.LINEAR, moderngl.LINEAR)
        
        self.program = self.shader_cache.get('screen')
        
        # Empty VAO for the screen triangle strip which is generated in the vertex shader
        self.vao = self.ctx.vertex_array(self.program, [])
        
    def play(self, skip_sec=2.0, fade_in_sec=1.0):
        if not self.valid:
            print("[VideoPlayer] Cannot play invalid video.")
            return
            
        clock = pygame.time.Clock()
        running = True
        
        if skip_sec > 0:
            self.cap.set(cv2.CAP_PROP_POS_MSEC, skip_sec * 1000.0)
            
        print(f"[VideoPlayer] Playing video {self.filepath} at {self.fps} FPS, skip={skip_sec}s, fade={fade_in_sec}s")
        start_ticks = pygame.time.get_ticks()
        
        while running:
            # Event handling
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    pygame.quit()
                    import sys
                    sys.exit()
                elif event.type == pygame.KEYDOWN:
                    # Allow skipping the intro
                    if event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE):
                        running = False
            
            if not running:
                break
                
            ret, frame = self.cap.read()
            if not ret:
                break # Video finished
                
            # OpenCV provides BGR, we need RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Apply fade in
            current_ticks = pygame.time.get_ticks()
            elapsed_sec = (current_ticks - start_ticks) / 1000.0
            if fade_in_sec > 0 and elapsed_sec < fade_in_sec:
                alpha = max(0.0, min(1.0, elapsed_sec / fade_in_sec))
                frame_rgb = cv2.convertScaleAbs(frame_rgb, alpha=alpha, beta=0)
            
            # OpenGL expects image origin at bottom-left, but OpenCV is top-left.
            # We must flip it vertically.
            frame_rgb = cv2.flip(frame_rgb, 0)
            
            # Write to texture
            self.texture.write(frame_rgb.tobytes())
            
            # Render to default framebuffer
            self.ctx.screen.use()
            self.ctx.clear(0, 0, 0)
            
            self.texture.use(location=0)
            if 'u_texture' in self.program:
                self.program['u_texture'].value = 0
                
            # Render using TRIANGLE_STRIP for 4 vertices
            self.vao.render(moderngl.TRIANGLE_STRIP, vertices=4)
            
            pygame.display.flip()
            clock.tick(self.fps)
            
    def destroy(self):
        if getattr(self, 'cap', None) and self.cap.isOpened():
            self.cap.release()
        if getattr(self, 'texture', None):
            self.texture.release()
        if getattr(self, 'vao', None):
            self.vao.release()
