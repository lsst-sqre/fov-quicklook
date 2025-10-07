
const vec3 colorTable[16] = vec3[](vec3(0.04503935, 0.01482344, 0.02092227), vec3(0.11370826, 0.06527747, 0.11536893), vec3(0.17566717, 0.11378321, 0.21857219), vec3(0.2213631, 0.16471913, 0.33041431), vec3(0.24905614, 0.22023618, 0.448113), vec3(0.24958205, 0.28556371, 0.55701246), vec3(0.22413977, 0.36487341, 0.60994938), vec3(0.20985996, 0.44238227, 0.62938329), vec3(0.20479718, 0.51702417, 0.64636539), vec3(0.20431921, 0.59140842, 0.66300179), vec3(0.220668, 0.66594665, 0.67485792), vec3(0.26993099, 0.73997282, 0.67917264), vec3(0.3759816, 0.80950627, 0.67641393), vec3(0.56798832, 0.85987893, 0.70468261), vec3(0.73475675, 0.90664718, 0.78615802), vec3(0.86429066, 0.95635719, 0.89067759));

vec3 colormap(float value) {
    value = clamp(value, 0.0, 1.0);
    int n = colorTable.length() - 1;
    float scaledValue = value * float(n);
    int index = int(floor(scaledValue));
    float fraction = scaledValue - float(index);
    index = clamp(index, 0, n);
    return mix(colorTable[index], colorTable[index + 1], fraction);
}
