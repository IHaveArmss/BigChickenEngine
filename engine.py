import pygame
import moderngl
from model import Triangle

class GraphicsEngine:
    def __init__(self,win_size = (800,600)):
        pygame.init()
        pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MAJOR_VERSION,3)
        pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MINOR_VERSION,3)
        pygame.display.gl_set_attribute(pygame.GL_CONTEXT_PROFILE_MASK, pygame.GL_CONTEXT_PROFILE_CORE)

        pygame.display.set_mode(win_size,flags = pygame.OPENGL | pygame.DOUBLEBUF)

        self.ctx = moderngl.create_context()

        self.scene = Triangle(self.ctx)

        self.clock = pygame.time.Clock()


    def check_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                self.scene.destroy()
                pygame.quit()
                exit()

    def render(self):

        self.ctx.clear(0.08,0.16,0.18)
        #asta self.scene.render deseneaza triunghiul
        self.scene.render()

        pygame.display.flip()

    def run(self):
        while(True):
            self.check_events()
            self.render()
            self.clock.tick(60)