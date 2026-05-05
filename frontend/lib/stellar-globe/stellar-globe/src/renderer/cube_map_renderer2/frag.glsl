precision mediump float;

uniform samplerCube u_cubeTexture;
uniform mat4 u_mMatrix;
uniform float u_alpha;
varying vec3 v_position;
varying float v_z;

void main() {
    gl_FragColor = textureCube(u_cubeTexture, (u_mMatrix * vec4(v_position, 1.)).yzx);
    gl_FragColor.a *= u_alpha * smoothstep(0., 0.4, v_z);
}