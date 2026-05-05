precision mediump float;

uniform sampler2D u_texture0;
uniform float u_layer_alpha;
uniform float u_alpha;
uniform vec4  u_color;
varying vec2 v_tCoord;

void main() {
    u_layer_alpha;
    gl_FragColor = texture2D(u_texture0, v_tCoord);
    gl_FragColor.rgb *= u_layer_alpha;
    gl_FragColor.a *= u_alpha;
    gl_FragColor *= u_color;
        // gl_FragColor.g += 0.5 * u_alpha;
}
