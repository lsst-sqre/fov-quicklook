precision mediump float;
varying   vec4   v_color;
varying   float  v_w;


void main() {
    float r = 2. * length(gl_PointCoord - vec2(0.5));
    float v = (1. - smoothstep(0.6, 1.0, r)) * clamp(4. * (v_w - 0.2), 0., 1.);
    gl_FragColor = v_color;
    gl_FragColor.a *= v;
}