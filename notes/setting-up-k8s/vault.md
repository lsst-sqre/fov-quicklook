## 開発用のVautlのセットアップ

* Vaultのインストール

    https://developer.hashicorp.com/vault/docs/platform/k8s/helm

    ```bash
    helm install --create-namespace -n vault vault hashicorp/vault --set "server.dev.enabled=true"
    ```

* Vault Operatorのインストール

    Phalanxでは https://github.com/ricoberger/vault-secrets-operator が動いていることが前提。

    ```bash
    helm repo add ricoberger https://ricoberger.github.io/helm-charts
    helm repo update

    helm upgrade --create-namespace --namespace vault --install vault-secrets-operator ricoberger/vault-secrets-operator
    ```

    operatorのdeploymentを編集し環境変数を追加

    ```yaml
        - name: VAULT_TOKEN_LEASE_DURATION
          value: "86400"
        - name: VAULT_TOKEN
          value: root
        - name: VAULT_ADDR
          value: http://vault:8200
    ```


`vault-0`に`kubectl exec`して、以下を実行。

```bash
vault kv put secret/fov-quicklook \
  s3_repository_access_key=quicklook \
  s3_repository_secret_key=password \
  s3_tile_access_key=quicklook \
  s3_tile_secret_key=password \
  db_password=password
```
