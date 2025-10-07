/*

dev serverでは `/fov-quicklook/api` へのリクエストを https://usdf-rsp-dev.slac.stanford.edu/fov-quicklook に転送する。
この時認証用のヘッダーを付加する必要がある。

認証用のヘッダーは `Cookie: gafaelfawr="..."` のようなものであるが、
この値はユーザーがブラウザで https://usdf-rsp-dev.slac.stanford.edu/fov-quicklook/ にアクセスし認証して取得する必要がある。
認証成功後、Safariの開発者ツールのネットワークタブでどれかのリクエストについて「cURLとしてコピー」を選択することで、この値を含んだ文字列を取得できる。
例えば次の様なものである。

```
curl 'https://usdf-rsp-dev.slac.stanford.edu/fov-quicklook/api/quicklooks' \
-X 'POST' \
-H 'Content-Type: application/json' \
-H 'Accept: "*"/"*"' \
-H 'Sec-Fetch-Site: same-origin' \
-H 'Accept-Language: ja' \
-H 'Accept-Encoding: gzip, deflate, br' \
-H 'Sec-Fetch-Mode: cors' \
-H 'Origin: https://usdf-rsp-dev.slac.stanford.edu' \
-H 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.4 Safari/605.1.15' \
-H 'Referer: https://usdf-rsp-dev.slac.stanford.edu/fov-quicklook/' \
-H 'Content-Length: 26' \
-H 'Connection: keep-alive' \
-H 'Sec-Fetch-Dest: empty' \
-H 'Cookie: gafaelfawr="xxx="; _ga_2BMBCFJ72S=GS1.1.1744597213.1.1.1744599045.0.0.0; _ga_4TNTC7E7PN=GS1.1.1744597213.1.1.1744599045.0.0.0; _ga_7FEJNFK38V=GS1.1.1744597213.1.1.1744599045.0.0.0; _ga=GA1.1.1184893326.1744597214' \
-H 'Priority: u=3, i' \
--data-raw '{"id":"raw:2025042300208"}'
```

このcurlコマンド文字列が .curl というファイルに保存されているとする。
getGafaelfawrTokenFromFileは .curl からcookieのgafaelfawr="..."の部分を抽出して返す関数である。

*/

// @ts-ignore
import fs from 'fs'
// @ts-ignore
import path from 'path'
// @ts-ignore
import { fileURLToPath } from 'url'

export function getGafaelfawrToken() {
  // ファイルのディレクトリパスを取得
  // @ts-ignore
  const __filename = fileURLToPath(import.meta.url)
  const __dirname = path.dirname(__filename)
  
  // 実行ファイルと同じディレクトリにある .curl ファイルへのパスを構築
  const file = path.join(__dirname, '.curl')
  const data = fs.readFileSync(file, 'utf8')
  const regex = /gafaelfawr="([^"]+)"/
  const match = data.match(regex)
  if (match) {
    return match[1]
  } else {
    throw new Error('gafaelfawr token not found in file')
  }
}
