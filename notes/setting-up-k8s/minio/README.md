## まとめ

* `da19` 〜 `da22` の4台でminioクラスターを構成。
* `mc cp`コマンドでは600MiB/s程度で読み書き可能。

## `mc`コマンドの使い方

```bash
docker run -e http_proxy= -e HTTP_PROXY= --network=host --rm --entrypoint /bin/bash -it -v $HOME/rubinviewer/data/shots:/shots quay.io/minio/minio:RELEASE.2024-08-26T15-33-07Z-cpuv1 --
```

```bash
mc alias set myminio http://127.0.0.1:9000 minio password
mc alias set myminio http://192.168.13.201:9000 minio password
mc mb myminio/quicklook-repository
mc mb myminio/quicklook-tile
# mc cp --recursive /shots/20230511PH/ myminio/mybucket/20230511PH
# mc rm --force -r myminio/mybucket/20230511P

cd /shots/20230511PH
for i in *.fits ; do ccd_name=$(echo $i | cut -d_ -f 5-6 | cut -d. -f 1) ; echo mc cp $i myminio/quicklook-repository/raw/broccoli/$ccd_name.fits ; done | bash -v

cd /shots/calexp-192350/
for i in *.fits ; do ccd_name=$(echo $i | cut -d_ -f9-10) ; echo mc cp $i myminio/quicklook-repository/calexp/192350/$ccd_name.fits ; done | sh -v
```

## 性能試験

 ### da12

```bash
cd iperf
docker build -t iperf .
docker save iperf:latest | ssh da13 "docker load"
docker run --network=host --rm -it iperf -s
```

```
docker run --network=host --rm -it iperf -s
-----------------------------------------------------------
Server listening on 5201
-----------------------------------------------------------
Accepted connection from 192.168.13.113, port 52884
[  5] local 192.168.13.112 port 5201 connected to 192.168.13.113 port 52886
[ ID] Interval           Transfer     Bitrate
[  5]   0.00-1.00   sec   563 MBytes  4.72 Gbits/sec
[  5]   1.00-2.00   sec   612 MBytes  5.13 Gbits/sec
[  5]   2.00-3.00   sec   514 MBytes  4.32 Gbits/sec
[  5]   3.00-4.00   sec   724 MBytes  6.07 Gbits/sec
[  5]   4.00-5.00   sec   523 MBytes  4.38 Gbits/sec
[  5]   5.00-6.00   sec   656 MBytes  5.50 Gbits/sec
[  5]   6.00-7.00   sec   675 MBytes  5.66 Gbits/sec
[  5]   7.00-8.00   sec   561 MBytes  4.71 Gbits/sec
[  5]   8.00-9.00   sec   685 MBytes  5.74 Gbits/sec
[  5]   9.00-10.00  sec   801 MBytes  6.72 Gbits/sec
[  5]  10.00-10.04  sec  23.2 MBytes  5.39 Gbits/sec
- - - - - - - - - - - - - - - - - - - - - - - - -
[ ID] Interval           Transfer     Bitrate
[  5]   0.00-10.04  sec  6.19 GBytes  5.29 Gbits/sec                  receiver
-----------------------------------------------------------
Server listening on 5201
-----------------------------------------------------------
```

### da13

```bash
docker run --network=host --rm -it iperf -c 192.168.13.112
```

```
[hsc@da13 ~]$ docker run --network=host --rm -it iperf -c 192.168.13.112
^EConnecting to host 192.168.13.112, port 5201
[  5] local 192.168.13.113 port 52886 connected to 192.168.13.112 port 5201
[ ID] Interval           Transfer     Bitrate         Retr  Cwnd
[  5]   0.00-1.00   sec   588 MBytes  4.93 Gbits/sec  589    230 KBytes
[  5]   1.00-2.00   sec   613 MBytes  5.14 Gbits/sec  791    307 KBytes
[  5]   2.00-3.00   sec   511 MBytes  4.29 Gbits/sec  820    280 KBytes
[  5]   3.00-4.00   sec   735 MBytes  6.17 Gbits/sec  536    344 KBytes
[  5]   4.00-5.00   sec   508 MBytes  4.26 Gbits/sec  651    309 KBytes
[  5]   5.00-6.00   sec   662 MBytes  5.56 Gbits/sec  1006    230 KBytes
[  5]   6.00-7.00   sec   671 MBytes  5.63 Gbits/sec  1064    173 KBytes
[  5]   7.00-8.00   sec   564 MBytes  4.73 Gbits/sec  660    315 KBytes
[  5]   8.00-9.00   sec   693 MBytes  5.81 Gbits/sec  805    434 KBytes
[  5]   9.00-10.00  sec   791 MBytes  6.64 Gbits/sec  898    230 KBytes
- - - - - - - - - - - - - - - - - - - - - - - - -
[ ID] Interval           Transfer     Bitrate         Retr
[  5]   0.00-10.00  sec  6.19 GBytes  5.32 Gbits/sec  7820             sender
[  5]   0.00-10.04  sec  6.19 GBytes  5.29 Gbits/sec                  receiver

iperf Done.
```

### PUT

2台, localhost 373MiB/s, 378MiB/s
2台, metalLB 300MiB/s, 300MiB/s
3台, localhost 800MiB/s
3台, metalLB 500MiB/s
4台, localhost 720MiB/s
4台, metalLB 480MiB/s
8台, localhost 529MiB/s
8台, metalLB 591MiB/s

```