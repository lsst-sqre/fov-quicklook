precision mediump float;

uniform float u_fovy;
varying vec4 v_color;
varying float v_y;
varying float v_w;

/**/
void main() {
    float alpha = 1. - smoothstep(0., 0.9, abs(v_y));
    alpha *= clamp(4. * (v_w - 0.2), 0., 1.);
    gl_FragColor = vec4(v_color.rgb, alpha * v_color.a);
}

/*/

void main() {
    // 線の中心からの距離を計算
    float edgeDistance = abs(v_y); // 中心からの距離

    // ぼかしを適用する閾値を設定
    float blurStart = 0.9; // ぼかしを開始する閾値
    float blurEnd = 1.0; // ぼかしを終了する閾値

    // smoothstepを使用して、端の1ピクセルのみをぼかす
    float alpha = 1. - smoothstep(blurStart, blurEnd, edgeDistance);

    // その他の透明度の調整
    alpha *= clamp(4. * (v_w - 0.2), 0., 1.);

    // 最終的な色の設定
    gl_FragColor = vec4(v_color.rgb, alpha * v_color.a);
}

/**/