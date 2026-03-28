#version 330 core

in vec2 v_uv;

uniform sampler2D u_texture;
uniform float u_alpha;

out vec4 frag_color;

void main() {
    vec4 tex_color = texture(u_texture, v_uv);
    frag_color = vec4(tex_color.rgb, tex_color.a * u_alpha);
}
