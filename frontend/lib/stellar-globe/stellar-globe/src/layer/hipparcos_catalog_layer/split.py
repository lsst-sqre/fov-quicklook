import argparse
import json
import shutil
import gzip
from pathlib import Path
from typing import Callable


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--n-div', '-n', type=int, default=20)
    parser.add_argument('--out', '-o', default='hipparcos-catalog')
    args = parser.parse_args()
    out = Path(args.out)
    n_div = args.n_div

    with open('./catalog.json') as f:
        hip = json.load(f)

    def i2fname(i): return f'part-{i}.json'

    shutil.rmtree(out, ignore_errors=True)
    save_gz_json(out / 'index.json', [i2fname(i) for i in range(n_div)])

    for name, s in hip.items():
        s.append(int(name))

    hip = list(hip.values())
    hip.sort(key=lambda a: a[2])

    for i, (start, end) in enumerate(division(n_div, len(hip), f=lambda x: x**2)):
        sub = hip[start:end]
        save_gz_json(out / i2fname(i), sub)


def save_gz_json(outfile: Path, data):
    outfile.parent.mkdir(parents=True, exist_ok=True)

    with outfile.open('w') as f:
        json.dump(data, f)

    with Path(f'{outfile}.gz').open('wb') as f:
        with gzip.open(f, mode='wb') as gf:
            gf.write(json.dumps(data).encode())


def division(n_div: int, n_items: int, f: Callable[[float], float]):
    start = 0
    for i in range(n_div):
        end = int(n_items * f(float(i + 1) / n_div))
        if i == n_div - 1:
            end = n_items
        yield start, end
        start = end


main()
