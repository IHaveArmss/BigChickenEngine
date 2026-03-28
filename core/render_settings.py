from dataclasses import dataclass


@dataclass
class RenderSettings:
    # Master
    ps2_enabled: bool = True

    # Postprocess (pixelation/quantize/dither)
    postprocess_enabled: bool = True
    pixel_size: int = 3  # screen pixels per block
    quantize_enabled: bool = True
    quantize_steps: int = 32  # per-channel steps (higher = smoother)
    dither_enabled: bool = False

    # Lighting style (in-shader)
    lighting_ramp_enabled: bool = True
    lighting_ramp_steps: int = 4
    specular_banding_enabled: bool = False
    specular_steps: int = 3

    # Optional PS1-ish wobble (vertex snapping)
    wobble_enabled: bool = False
    wobble_pixel_size: int = 2

    # Directional shadow settings
    directional_shadows_enabled: bool = True
    directional_shadow_resolution: int = 2048
    directional_shadow_distance: float = 40.0
    shadow_bias: float = 0.003

    # Spot shadow settings (limited budget)
    spot_shadows_enabled: bool = True
    max_shadowed_spot_lights: int = 4
    spot_shadow_resolution: int = 512

    # Lighting tuning
    ambient_strength: float = 0.15
    ambient_color_r: float = 1.0
    ambient_color_g: float = 1.0
    ambient_color_b: float = 1.0
    sun_azimuth_deg: float = 45.0
    sun_elevation_deg: float = -55.0
    sun_intensity: float = 1.0   # 0.0 = no sun (indoor), 1.0 = full sun

    # Skybox
    skybox_path: str = ''  # path to equirectangular sky image, empty = no skybox

