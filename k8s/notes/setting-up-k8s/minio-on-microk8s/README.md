### MinIOのインストール

```bash
microk8s enable minio
# しばらく待つ
kubectl -n minio-operator edit csv minio-console # typeをNodePortに変更
# パスワード確認
TENANT_NAME="microk8s"
microk8s kubectl get -n minio-operator secret $TENANT_NAME-env-configuration -o jsonpath='{.data.config\.env}' | base64 -d
# この情報でconsoleにログインできる
# 何かbucketを作っておく
```

### `mc`のインストール

```bash
curl -O https://dl.min.io/client/mc/release/linux-amd64/mc
chmod +x mc
sudo mv mc /usr/local/bin/
# alias設定
bash ./mc-alias
mc ls microk8s
```

### サンプルデータのアップロード