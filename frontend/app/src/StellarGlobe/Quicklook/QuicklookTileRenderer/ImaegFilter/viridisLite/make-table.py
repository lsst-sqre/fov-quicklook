import argparse
import csv
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import cast


def main():
    @dataclass
    class Args:
        out_dir: Path
        n_div: int

    parser = argparse.ArgumentParser()
    parser.add_argument('--n_div', type=int, default=16)
    parser.add_argument('--out_dir', type=Path, default=Path('.'))
    args = Args(**vars(parser.parse_args()))

    os.chdir(Path(__file__).parent)
    if not Path('viridisLite').exists():
        os.system('git clone https://github.com/sjmgarnier/viridisLite && cd viridisLite && git reset --hard v0.4.2CRAN')

    for data_file in Path('./viridisLite/data-raw').glob('*.csv'):
        out_file = args.out_dir / 'colormap' / f'{file_name_to_colormap_name(data_file.name)}.glsl'
        make_shader(data_file, out_file, args.n_div)

    for data_file in Path('./viridisLite/data-raw').glob('*.csv'):
        out_file = args.out_dir / 'json' / f'{file_name_to_colormap_name(data_file.name)}.json'
        make_json(data_file, out_file, args.n_div)


def file_name_to_colormap_name(file_name: str) -> str:
    #'  \itemize{
    #'   \item "magma" (or "A")
    #'   \item "inferno" (or "B")
    #'   \item "plasma" (or "C")
    #'   \item "viridis" (or "D")
    #'   \item "cividis" (or "E")
    #'   \item "rocket" (or "F")
    #'   \item "mako" (or "G")
    #'   \item "turbo" (or "H")
    #'  }
    return {
        'optionA.csv': 'magma',
        'optionB.csv': 'inferno',
        'optionC.csv': 'plasma',
        'optionD.csv': 'viridis',
        'optionE.csv': 'cividis',
        'optionF.csv': 'rocket',
        'optionG.csv': 'mako',
        'optionH.csv': 'turbo',
        'viridis_map.csv': 'viridis',
    }[file_name]


type v3 = tuple[float, float, float]


def make_shader(data_file: Path, out_file: Path, n_div: int):
    with data_file.open() as f:
        reader = csv.reader(f)
        next(reader)
        table: list[v3] = [cast(v3, tuple([*map(float, row)])) for row in reader]

    # 間引いたテーブルを作成
    sampled_points = [interpolate(table, x) for x in [i / (n_div - 1) for i in range(n_div)]]
    colors_in_shader = ', '.join([f'vec3({r}, {g}, {b})' for r, g, b in sampled_points])

    shader = f'''
const vec3 colorTable[{n_div}] = vec3[]({colors_in_shader});

vec3 colormap(float value) {{
    value = clamp(value, 0.0, 1.0);
    int n = colorTable.length() - 1;
    float scaledValue = value * float(n);
    int index = int(floor(scaledValue));
    float fraction = scaledValue - float(index);
    index = clamp(index, 0, n - 1);
    return mix(colorTable[index], colorTable[index + 1], fraction);
}}
'''
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with out_file.open('w') as f:
        f.write(shader)


def make_json(data_file: Path, out_file: Path, n_div: int):
    with data_file.open() as f:
        reader = csv.reader(f)
        next(reader)
        table: list[v3] = [cast(v3, tuple([*map(float, row)])) for row in reader]

    # 間引いたテーブルを作成
    sampled_points = [interpolate(table, x) for x in [i / (n_div - 1) for i in range(n_div)]]
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with out_file.open('w') as f:
        json.dump(sampled_points, f)


def interpolate(table: list[v3], value: float) -> v3:
    value = min(max(value, 0.0), 1.0)
    n = len(table) - 1
    scaled_value = value * n
    index = int(scaled_value)
    fraction = scaled_value - index
    index = min(max(index, 0), n - 1)
    return cast(
        v3,
        tuple([table[index][i] * (1 - fraction) + table[index + 1][i] * fraction for i in range(3)]),
    )


if __name__ == '__main__':
    main()
