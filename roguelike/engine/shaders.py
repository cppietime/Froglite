import numpy as np

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .renderer import Renderer

"""
Just another helper file to register all the shaders and special VAOs
"""

_quad_vertex_src = \
"""
#version 330
layout (location=0) in vec2 in_position;
layout (location=1) in vec2 in_uv;

out vec2 out_uv;

uniform vec2 center_pos;
uniform vec2 pre_scale;
uniform vec2 post_scale;
uniform float angle;
uniform float z;
uniform vec2 uv_bottom_left;
uniform vec2 uv_size;

void main() {
    vec2 scaled = post_scale * in_position;
    float c = cos(angle);
    float s = sin(angle);
    vec2 rot = vec2(scaled.x * c - scaled.y * s, scaled.y * c + scaled.x * s);
    rot = pre_scale * rot;
    
    gl_Position = vec4(rot + center_pos, z, 1.0);
    out_uv = vec2(uv_bottom_left + in_uv * uv_size);
}
"""

def register_shaders(renderer: 'Renderer') -> None:
    renderer.register_program('quad', vertex_shader=_quad_vertex_src,
            fragment_shader=
"""
#version 330
in vec2 out_uv;

layout (location=0) out vec4 fragColor;

uniform sampler2D tex;
uniform vec4 colorMask;

void main() {
    fragColor = texture(tex, out_uv) * colorMask;
}
""", varyings = ('out_uv',))
        
    quad_buffer = np.array([
        -1, -1, 0, 0,
        1, -1, 1, 0,
        1, 1, 1, 1,
        -1, -1, 0, 0,
        1, 1, 1, 1,
        -1, 1, 0, 1
    ], dtype='float32')
    renderer.register_vao('quad',
                          renderer.programs['quad'],
                          ((quad_buffer, '2f4 2f4', 'in_position', 'in_uv'),))

    renderer.register_program('extract_bloom',
                              vertex_shader=_quad_vertex_src,
                              fragment_shader=
"""
#version 330
in vec2 out_uv;

layout (location=0) out vec4 bloomColor;

uniform float threshold;
uniform sampler2D tex;

void main() {
    vec4 in_color = texture(tex, out_uv);
    /* I will probably want to change this to a better luminocity formula */
    float lum = in_color.x * .333 + in_color.y * .333 + in_color.z * .333;
    bloomColor = (lum >= threshold) ? vec4(in_color) : vec4(0);
}
""", varyings = ('out_uv',))
    renderer.register_vao('extract_bloom',
                          renderer.programs['extract_bloom'],
                          ((quad_buffer, '2f4 2f4', 'in_position', 'in_uv'),))
    
    renderer.register_program('blur',
                              vertex_shader=_quad_vertex_src,
                              fragment_shader=
"""
#version 330
in vec2 out_uv;

layout (location=0) out vec4 blurColor;

uniform uint blurSize;
uniform int horizontal;
uniform sampler2D tex;

const float irt2pi = .39894228;

void main() {
    vec2 pixelSize = 1.0 / textureSize(tex, 0);
    float sigma = float(blurSize) / 3.0f;
    float den = 1.0 / (2.0 * sigma * sigma);
    vec3 accum = texture(tex, out_uv).rgb * irt2pi;
    for (uint i = 1U; i <= blurSize; i++) {
        float factor = irt2pi * exp(-int(i * i) * den) / sigma;
        if (horizontal != 0) {
            accum += texture(tex, out_uv + vec2(pixelSize.x * i, 0)).rgb
                * factor;
            accum += texture(tex, out_uv - vec2(pixelSize.x * i, 0)).rgb
                * factor;
        }
        else {
            accum += texture(tex, out_uv + vec2(0, pixelSize.y * i)).rgb
                * factor;
            accum += texture(tex, out_uv - vec2(0, pixelSize.y * i)).rgb
                * factor;
        }
    }
    blurColor = vec4(accum, 1);
}
""", varyings=('out_uv',))
    renderer.register_vao('blur',
                          renderer.programs['blur'],
                          ((quad_buffer, '2f4 2f4', 'in_position', 'in_uv'),))
    
    renderer.register_program('add',
                              vertex_shader=_quad_vertex_src,
                              fragment_shader=
"""
#version 330
in vec2 out_uv;

layout (location=0) out vec4 sumColor;

uniform sampler2D tex;
uniform sampler2D addition;
uniform float factor;

void main() {
    vec3 baseColor = texture(tex, out_uv).rgb;
    vec3 addColor = texture(addition, out_uv).rgb * factor + baseColor;
    //addColor = vec3(1) - exp(-addColor * 1.5);
    //addColor = pow(addColor, vec3(1.0 / 2.2));
    // I think I will move HDR + gamma into a separate shader
    sumColor = vec4(addColor, 1);
}
""", varyings=('out_uv',))
    renderer.register_vao('add',
                          renderer.programs['add'],
                          ((quad_buffer, '2f4 2f4', 'in_position', 'in_uv'),))
    
    renderer.register_program('gamma',
                              vertex_shader=_quad_vertex_src,
                              fragment_shader=
"""
#version 330
in vec2 out_uv;

layout (location=0) out vec4 fragColor;

uniform sampler2D tex;
uniform float gamma = 2.2;
uniform float exposure = 1.0;

void main() {
    vec3 base = texture(tex, out_uv).rgb;
    base = vec3(1) - exp(-base * exposure);
    base = pow(base, vec3(1.0 / gamma));
    fragColor = vec4(base, 1);
}
""", varyings=('out_uv',))
    renderer.register_vao('gamma',
                          renderer.programs['gamma'],
                          ((quad_buffer, '2f4 2f4', 'in_position', 'in_uv'),))
    
    renderer.register_program('vignette',
                              vertex_shader=_quad_vertex_src,
                              fragment_shader=
"""
#version 330
in vec2 out_uv;

layout (location=0) out vec4 fragColor;

uniform sampler2D tex;
uniform sampler2D mask;

void main() {
    vec4 baseColor = texture(tex, out_uv);
    float mask = texture(mask, out_uv).r; // Will use red
    baseColor.a *= mask;
    fragColor = baseColor;
}
""", varyings=('out_uv',))
    renderer.register_vao('vignette',
                          renderer.programs['vignette'],
                          ((quad_buffer, '2f4 2f4', 'in_position', 'in_uv'),))
        