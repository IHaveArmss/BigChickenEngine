#version 330 core

in vec3 v_frag_pos;
in vec3 v_normal;
in vec2 v_texcoord;

uniform vec3 u_light_pos;
uniform vec3 u_light_color;
uniform vec3 u_object_color;
uniform vec3 u_view_pos;

uniform sampler2D u_texture;
uniform bool u_use_texture;

out vec4 frag_color;

void main() {
    // Base color — from texture or uniform
    vec3 base_color;
    if (u_use_texture) {
        base_color = texture(u_texture, v_texcoord).rgb;
    } else {
        base_color = u_object_color;
    }

    // --- Ambient ---
    float ambient_strength = 0.2;
    vec3 ambient = ambient_strength * u_light_color;

    // --- Diffuse ---
    vec3 norm = normalize(v_normal);
    vec3 light_dir = normalize(u_light_pos - v_frag_pos);
    float diff = max(dot(norm, light_dir), 0.0);
    vec3 diffuse = diff * u_light_color;

    // --- Specular (Blinn-Phong) ---
    float specular_strength = 0.3;
    vec3 view_dir = normalize(u_view_pos - v_frag_pos);
    vec3 halfway = normalize(light_dir + view_dir);
    float spec = pow(max(dot(norm, halfway), 0.0), 32.0);
    vec3 specular = specular_strength * spec * u_light_color;

    vec3 result = (ambient + diffuse + specular) * base_color;
    frag_color = vec4(result, 1.0);
}
