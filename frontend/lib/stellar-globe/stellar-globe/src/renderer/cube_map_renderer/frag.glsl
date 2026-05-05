precision mediump float;

uniform    samplerCube   u_cubeTexture;
uniform    mat4          u_mMatrix;
uniform    float         u_radius;
uniform    float         u_alpha;
uniform    vec3          u_eyePosition;
varying    vec3          v_position;

void main() {
    vec3 d = v_position - u_eyePosition;
    float a = dot(d, d),
          b = 2. * dot(u_eyePosition, d),
          c = dot(u_eyePosition, u_eyePosition) - u_radius*u_radius,
          D = b*b - 4.*a*c,
          t1, t2;
    if (D < 0.)
        discard;
    t1 = (-b + sqrt(D)) / (2.*a);
    t2 = (-b - sqrt(D)) / (2.*a);
    vec3 dir1 = u_eyePosition + t1*d;
    vec3 dir2 = u_eyePosition + t2*d;
    float z = t2 * length(d);
    gl_FragColor = textureCube(u_cubeTexture, (u_mMatrix * vec4(dir1, 1.)).yzx) +
                   vec4(vec3(smoothstep(0., 1., z)), 0.) * textureCube(u_cubeTexture, (u_mMatrix * vec4(dir2, 1.)).yzx);

    gl_FragColor.rgb = pow(gl_FragColor.rgb, vec3(1.));
    // gl_FragColor = textureCube(u_cubeTexture, (u_mMatrix * vec4(dir1, 1.)).yzx);
    gl_FragColor.a *= u_alpha;
}