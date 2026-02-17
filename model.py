import numpy as np
import moderngl

class Triangle:

    def __init__ (self,ctx):
        self.ctx = ctx

        self.vbo = self.get_vbo()
        self.program = self.get_program("default")
        self.vao = self.get_vao()


    def get_vao(self):

        vao = self.ctx.vertex_array(self.program,[(self.vbo,'3f','in_position')])
        return vao

    def get_vbo(self):

        vertex_data = [#triangl
            -0.6, -0.6, 0.0,  # Bottom Left
            0.6, -0.6, 0.0,  # Bottom Righ
            0.0, 0.6, 0.0  # Top center
        ]

        vertex_data = np.array(vertex_data,dtype = 'f4')
        vbo = self.ctx.buffer(vertex_data)
        return vbo


    def get_program(self,shader_name):
        with open(f'shaders/{shader_name}.vert') as file:
            vertex_shader = file.read()

        with open(f'shaders/{shader_name}.frag') as file:
            fragment_shader = file.read()

        program = self.ctx.program(vertex_shader=vertex_shader,fragment_shader=fragment_shader)
        return program

    def render(self):
        self.vao.render()

    def destroy(self):
        self.vbo.release()
        self.program.release()
        self.vao.release()
