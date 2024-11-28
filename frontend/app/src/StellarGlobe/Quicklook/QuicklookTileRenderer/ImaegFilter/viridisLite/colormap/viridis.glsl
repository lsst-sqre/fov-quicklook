
const vec3 colorTable[16] = vec3[](vec3(0.26700401, 0.00487433, 0.32941519), vec3(0.28265633, 0.10019576, 0.42216032), vec3(0.27713437, 0.18522836, 0.48989831), vec3(0.25393498, 0.26525384, 0.52998273), vec3(0.22198915, 0.33916114, 0.54875211), vec3(0.19063135, 0.40706148, 0.55608907), vec3(0.16362543, 0.47113278, 0.55814842), vec3(0.13914708, 0.53381201, 0.55529773), vec3(0.12056501, 0.59642187, 0.54361058), vec3(0.13469183, 0.65863619, 0.5176488), vec3(0.20803045, 0.71870095, 0.4728733), vec3(0.3277958, 0.77397953, 0.40664011), vec3(0.47750446, 0.82144351, 0.31819529), vec3(0.64725685, 0.85839991, 0.20986086), vec3(0.82494028, 0.88472036, 0.10621724), vec3(0.98386829, 0.90486726, 0.13689671));

vec3 colormap(float value) {
    value = clamp(value, 0.0, 1.0);
    int n = colorTable.length() - 1;
    float scaledValue = value * float(n);
    int index = int(floor(scaledValue));
    float fraction = scaledValue - float(index);
    index = clamp(index, 0, n);
    return mix(colorTable[index], colorTable[index + 1], fraction);
}
