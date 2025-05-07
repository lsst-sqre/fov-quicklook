# Trouble Shooting

## usdfのネットワークトラブル

usdfではしばしばネットワークの不調があり、各コンポーネント間の通信が失敗しシステムが動かなくなる。
ここで、fov-quicklookのネットワークについて整理する。

### 通信ノードの組み合わせ

* frontend - coordinator
* coordinator - generator
* generator - embargo-storage
* generator - user-storage
