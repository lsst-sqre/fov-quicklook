# DAシリーズへのmicrok8sのインストールのメモ

## microk8sのインストール

### snapdのインストール

各ノードで↓を行う

```bash
# snapのインストール
export 'http_proxy=http://192.168.13.112:3128'
export 'https_proxy=http://192.168.13.112:3128'
export 'no_proxy=da*,localhost,127.0.0.1'
sudo -E yum --disableplugin='*' --disablerepo='*' --enablerepo='C7.9.2009-extras' -y install epel-release
sudo -E yum --disableplugin='*' --disablerepo='*' --enablerepo='epel,C7.9.2009-base,C7.9.2009-extras,C7.9.2009-updates' -y install snapd

# snapの設定
sudo systemctl enable snapd
sudo systemctl start snapd
sudo snap set system proxy.http=http://localhost:3128
sudo snap set system proxy.https=http://localhost:3128
sudo ln -s /var/lib/snapd/snap /snap
```

### microk8sのインストール

`da12`で行う

```bash
# 各ノードにmicrok8sのインストール
cat ./install-microk8s.bash | clush -o -A -w hsc@da'[12-22]' sudo bash
```

```bash
sudo /snap/bin/microk8s.config > ~/.kube/config
vi ~/.kube/config
# server: https://192.168.1.112:16443
# ↓と書き換え
# server: https://192.168.13.112:16443
kubectl get node
```


```bash
# control planeのインストール
for i in {13..14} ; do
  echo $i
  cmd="$(sudo /snap/bin/microk8s add-node | grep 13.112)"
  ssh -A da$i sudo /snap/bin/$cmd
done

# workerのインストール
for i in {15..22} ; do
  echo $i
  cmd="$(sudo /snap/bin/microk8s add-node | grep 13.112)"
  ssh -A da$i sudo /snap/bin/$cmd --worker
done
```

### addondの有効化

`da12`で行う

```bash
# ここは多分うまく動かない。１行ずつチェック
# http-proxyの問題。
for addon in \
  dns:1.1.1.1 \
  metallb:192.168.13.200-192.168.13.210 \
  ingress \
  metrics-server \
  observability \
  hostpath-storage \
  rbac \
  registry
do
  /snap/bin/microk8s enable $addon
done
```

### MetalLBが`Error: secret "memberlist" not found`で動かない場合は

```bash
kubectl create secret generic -n metallb-system memberlist --from-literal=secretkey="$(openssl rand -base64 128)"
```

> https://github.com/kubernetes-sigs/kind/issues/1449#issuecomment-616319066

### IngressをMetalLBで有効化

```bash
kubectl apply -n ingress -f ./ingress-metallb.service.yaml
```

### MinIOのインストール

```bash
for i in {12..22} ; do
  kubectl label nodes da$i minio-
done
for i in {21..22} ; do
  kubectl label nodes da$i minio=true
done

clush -o -A -w hsc@da'[12-22]' sudo rm -rf /mnt/ssd1/minio
clush -o -A -w hsc@da'[12-22]' sudo mkdir -p /mnt/ssd1/minio
kubectl create namespace minio
kubectl -n minio apply -f ./minio/minio.daemonset.yaml
kubectl -n minio apply -f ./minio/minio.service.yaml
```

## 設定後

* Ingress
  * `192.168.13.200:{80,443}`で動作
* MinIO
  * 管理画面が`192.168.13.{12...22}:9001`で動作
  * s3インターフェースが`192.168.13.201:9000`で動作


## MinIOへのデータのアップロード

```bash
docker run -e http_proxy= -e HTTP_PROXY= --network=host --rm --entrypoint /bin/bash -it -v /mnt/ssd1/rawdata:/rawdata quay.io/minio/minio:RELEASE.2024-08-26T15-33-07Z-cpuv1 --
```

* GUIで２つのバケット`fov-quicklook-{repository,tile}`を作る

```bash
mc alias set myminio http://192.168.13.201:9000 minio password
mc mb myminio/fov-quicklook-repository
mc mb myminio/fov-quicklook-tile
mc mirror --overwrite /rawdata/minio/ myminio/fov-quicklook-repository

```

```
mkdir -p minio/raw/broccoli
mkdir -p minio/calexp/192350
# for i in 20230511PH/*.fits ; echo cp $i minio/raw/broccoli/(string replace -r '.*_(R.._S..\.fits)' '$1' $i) ; end | sh -v
# for i in ./calexp-192350/*.fits ; echo cp $i minio/calexp/192350/(string replace -r  -r '.*_(R.._S..)_.*' '$1' $i).fits ; end | sh -v
for i in 20230511PH/*.fits ; echo ln -s ../../../$i minio/raw/broccoli/(string replace -r '.*_(R.._S..\.fits)' '$1' $i) ; end | sh -v
for i in ./calexp-192350/*.fits ; echo ln -s ../../../$i minio/calexp/192350/(string replace -r  -r '.*_(R.._S..)_.*' '$1' $i).fits ; end | sh -v
```
