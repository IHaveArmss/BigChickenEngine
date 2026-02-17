#version 330 core

in vec2 v_uv;
uniform sampler2D u_texture;
out vec4 frag_color;

void main() {
    frag_color = texture(u_texture, v_uv);
}
