precision mediump float;
uniform sampler2D u_texture1;
uniform sampler2D u_shiftmap;
uniform mat3 u_tMatrix;
uniform float u_alpha;
varying vec2 v_coord;
varying float v_w;

const float DELTA_MAP_N = 64.; // This value must equal to valeu of DELTA_MAP_N in interface.ts

/*
    // TypeScript
    function encode(v: number) {
        const VMAX = 0.015
        return ((v / VMAX) + 1) / 2 * 256
    }
*/

const float VMAX = 0.015;
vec2 decode_shiftmap(vec2 e) {
    e *= 255. / 256.;
    return (2. * e - 1.) * VMAX;
}

vec2 delta_coord(vec2 c) {
    return (1. / DELTA_MAP_N) * ((DELTA_MAP_N - 1.) * c + vec2(0.5));
}

void main() {
    vec2 tCoord = (u_tMatrix * vec3(v_coord - decode_shiftmap(texture2D(u_shiftmap, delta_coord(v_coord)).xy), 1)).xy;
    gl_FragColor = texture2D(u_texture1, tCoord);
    gl_FragColor.a *= u_alpha * clamp(4. * (v_w - 0.2), 0., 1.);
    // vec2 d = pow(2. * (v_coord - vec2(0.5)), vec2(10.));
    // gl_FragColor.g += 0.75 * dot(d, d);
}