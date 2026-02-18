#version 330 core

in vec3 v_frag_pos;
in vec3 v_normal;
in vec2 v_texcoord;

// Change this number to support more or fewer lights
#define MAX_LIGHTS 8

uniform int u_num_lights;
uniform vec3 u_light_pos[MAX_LIGHTS];
uniform vec3 u_light_color[MAX_LIGHTS];

uniform vec3 u_object_color;
uniform vec3 u_view_pos;
uniform float u_alpha;

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

    vec3 norm = normalize(v_normal);
    vec3 view_dir = normalize(u_view_pos - v_frag_pos);

    // Ambient (applied once, using first light's color)
    float ambient_strength = 0.15;
    vec3 ambient = ambient_strength * (u_num_lights > 0 ? u_light_color[0] : vec3(1.0));

    // Accumulate diffuse + specular from all lights
    vec3 total_diffuse = vec3(0.0);
    vec3 total_specular = vec3(0.0);

    for (int i = 0; i < u_num_lights && i < MAX_LIGHTS; i++) {
        vec3 light_dir = normalize(u_light_pos[i] - v_frag_pos);

        // Diffuse
        float diff = max(dot(norm, light_dir), 0.0);
        total_diffuse += diff * u_light_color[i];

        // Specular (Blinn-Phong)
        vec3 halfway = normalize(light_dir + view_dir);
        float spec = pow(max(dot(norm, halfway), 0.0), 32.0);
        total_specular += 0.3 * spec * u_light_color[i];
    }

    vec3 result = (ambient + total_diffuse + total_specular) * base_color;
    frag_color = vec4(result, u_alpha);
}
