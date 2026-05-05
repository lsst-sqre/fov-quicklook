uniform    mat4   u_pvMatrix;
uniform    mat4   u_mMatrix;
uniform    mat3   u_texMatrix;
uniform    mat3   u_tileMatrix;
attribute  vec2   a_coord;
varying    vec2   v_tCoord;


void main(void) {
    v_tCoord = (u_texMatrix * vec3(a_coord, 1.)).xy;
    vec4 position = u_mMatrix * vec4((u_tileMatrix * vec3(v_tCoord, 1.)).xy, 0., 1.);
    // position.xyz /= vec3(length(position.xyz)); // for fd2u
    gl_Position = u_pvMatrix * position;
}
