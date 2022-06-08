import moderngl as mgl
import numpy as np

_quad_vertex_src = \
"""
#version 330
layout (location=0) in vec2 in_position;
layout (location=1) in vec2 in_uv;

out vec2 out_uv;

uniform vec2 center_pos;
uniform vec2 scale;
uniform float angle;
uniform float z;
uniform vec2 uv_bottom_left;
uniform vec2 uv_size;

void main() {
    vec2 scaled = scale * in_position;
    float c = cos(angle);
    float s = sin(angle);
    vec2 rot = vec2(scaled.x * c - scaled.y * s, scaled.y * c + scaled.x * s);
    
    gl_Position = vec4(rot + center_pos, z, 1.0);
    out_uv = vec2(uv_bottom_left + in_uv * uv_size);
}
"""

class Renderer:
    def __init__(self, gl_ctx):
        self.gl_ctx = gl_ctx
        self.programs = {}
        self.vaos = {}
        self.fbos = {}
        self.create_defaults()
    
    def register_program(self, name, vertex_shader, fragment_shader, varyings=()):
        program = self.gl_ctx.program(vertex_shader=vertex_shader, fragment_shader=fragment_shader, varyings=varyings)
        self.programs[name] = program
        return program
    
    def register_vao(self, name, program, buffer_specs):
        _buffer_specs = []
        for spec in buffer_specs:
            array = spec[0]
            buffer = self.gl_ctx.buffer(array)
            _buffer_specs.append((buffer, *spec[1:]))
        vao = self.gl_ctx.vertex_array(program, _buffer_specs)
        self.vaos[name] = vao
        return vao
    
    def register_fbo(self, name, size, num_tex, depth=True):
        textures = []
        for _ in range(num_tex):
            texture = self.gl_ctx.texture(size, 4)
            textures.append(texture)
        depth_att = None
        if depth:
            depth_att = self.gl_ctx.depth_texture(size)
        fbo = self.gl_ctx.framebuffer(tuple(textures), depth_att)
        self.fbos[name] = fbo
        return fbo
    
    def create_defaults(self):
        quad_program = self.register_program('quad', vertex_shader=_quad_vertex_src,
            fragment_shader=\
"""
#version 330
in vec2 out_uv;

layout (location=0) out vec4 fragColor;

uniform sampler2D tex;

void main() {
    fragColor = texture(tex, out_uv);
}
""", varyings = ('out_uv'))
        
        quad_buffer = np.array([
            -1, -1, 0, 0,
            1, -1, 1, 0,
            1, 1, 1, 1,
            -1, -1, 0, 0,
            1, 1, 1, 1,
            -1, 1, 0, 1
        ], dtype='float32')
        self.register_vao('quad', self.programs['quad'],\
            ((quad_buffer, '2f4 2f4', 'in_position', 'in_uv'),))
    
        # TODO I also want shaders for bloom effect and alpha masking, possibly other things too
        self.register_program('extract_bloom', vertex_shader=_quad_vertex_src,
            fragment_shader=\
"""
#version 330
in vec2 out_uv;

layout (location=0) out vec4 bloomColor;

uniform float threshold;
uniform sampler2D tex;

void main() {
    vec4 in_color = texture(tex, out_uv);
    float lum = in_color.x * .25 + in_color.y * .5 + in_color.z * .25;
    bloomColor = (lum >= threshold) ? vec4(in_color) : vec4(0);
}
""", varyings = ('out_uv'))
        self.register_vao('ex_bloom_quad', self.programs['extract_bloom'],\
            ((quad_buffer, '2f4 2f4', 'in_position', 'in_uv'),))
        
        self.register_program('blur', vertex_shader=_quad_vertex_src,
            fragment_shader=\
"""
#version 330
in vec2 out_uv;

layout (location=0) out vec4 blurColor;

uniform uint blurSize;
uniform bool horizontal;
uniform sampler2D tex;

const float irt2pi = .39894228;

void main() {
    vec2 pixelSize = 1 / textureSize(tex, 0);
    float sigma = float(blurSize) / 6.0f;
    float den = 1 / (2 * sigma * sigma);
    vec4 accum = texture(tex, out_uv) * irt2pi;
    for (uint i = 1U; i <= blurSize; i++) {
        float factor = irt2pi * exp(-int(i * i) * den);
        if (horizontal) {
            accum += texture(tex, out_uv + vec2(pixelSize.x * i, 0)) * factor;
            accum += texture(tex, out_uv - vec2(pixelSize.x * i, 0)) * factor;
        }
        else {
            accum += texture(tex, out_uv + vec2(0, pixelSize.y * i)) * factor;
            accum += texture(tex, out_uv - vec2(0, pixelSize.y * i)) * factor;
        }
    }
    blurColor = accum;
}
""", varyings=('out_uv'))
        self.register_vao('blur', self.programs['blur'],\
            ((quad_buffer, '2f4 2f4', 'in_position', 'in_uv'),))
        
        self.register_fbo('pingpong0', self.gl_ctx.screen.size, 1)
        self.register_fbo('pingpong1', self.gl_ctx.screen.size, 1)
