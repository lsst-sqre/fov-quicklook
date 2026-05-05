# equivalent to: ./generateSampleCsv.ts

'''
prompt for ChatGPT4:

次のようなCSVをつくるPythonスクリプトを作ってください。

* Python3.11用
* 型ヒントつき
* 次のようなCSVを生成する

# object_id,ra,dec,value1,value2,color,marker_type
123,30.4,40.,a,b,#fff,diamond
124,30.5,42.4,c,d,#f0f,circle
...

* ra, dec はとある範囲ないの乱数
* value1, value2は適当なランダムな文字列
* colorは #0000 〜 #ffff の形式の乱数
  * 最後の一文字は透明度なのでfまたは7
# marker_type はつぎのどれか "circle" | "plus" | "x" | "hollowPlus" | "hollowX" | "dot" | "circledHollowPlus" | "circledHollowX" | "diamond" | "square" | "asterisk" | "hollowAsterisk" | "circledHollowAsterisk" | "triangle" | "pentagon"
* ra, decの範囲、行数、color, marker_typeカラムの有無をコマンドライン引数から設定できる
  * 適当なデフォルト値もある
* CSVは標準出力に書き出す。

'''

import argparse
import random
import string
from typing import Tuple


def generate_random_string(length: int = 5) -> str:
    """Generates a random string of given length."""
    return ''.join(random.choices(string.ascii_lowercase, k=length))


def generate_random_color() -> str:
    """Generates a random color in the format #RRGGBB where the last digit is f or 7."""
    color = "#{:06x}".format(random.randint(0, 0xFFFFFE))
    return color[:-1] + random.choice('f7')


def generate_csv(ra_range: Tuple[float, float], dec_range: Tuple[float, float], num_rows: int, include_color: bool, include_marker_type: bool) -> None:
    """Generates a CSV file with specified options."""
    marker_types = ["circle", "plus", "x", "hollowPlus", "hollowX", "dot", "circledHollowPlus", "circledHollowX", "diamond", "square", "asterisk", "hollowAsterisk", "circledHollowAsterisk", "triangle", "pentagon"]
    headers = ["# object_id", "ra", "dec", "value1", "value2"]
    if include_color:
        headers.append("color")
    if include_marker_type:
        headers.append("marker_type")

    print(','.join(headers))
    for i in range(num_rows):
        row = [str(i + 123), str(random.uniform(*ra_range)), str(random.uniform(*dec_range)), generate_random_string(), generate_random_string()]
        if include_color:
            row.append(generate_random_color())
        if include_marker_type:
            row.append(random.choice(marker_types))

        print(','.join(row))


def main():
    parser = argparse.ArgumentParser(description="Generate a CSV file with random data.")
    parser.add_argument("--ra_min", type=float, default=0.0, help="Minimum RA value")
    parser.add_argument("--ra_max", type=float, default=1.0, help="Maximum RA value")
    parser.add_argument("--dec_min", type=float, default=-0.5, help="Minimum Dec value")
    parser.add_argument("--dec_max", type=float, default=0.5, help="Maximum Dec value")
    parser.add_argument("--num_rows", type=int, default=1000, help="Number of rows in the CSV")
    parser.add_argument("--include_color", action="store_true", help="Include color column")
    parser.add_argument("--include_marker_type", action="store_true", help="Include marker type column")

    args = parser.parse_args()

    generate_csv((args.ra_min, args.ra_max), (args.dec_min, args.dec_max), args.num_rows, args.include_color, args.include_marker_type)


if __name__ == "__main__":
    main()
