set -x

addr=$(/usr/sbin/ip a | perl -nle 'print $1 if /(192\.168\.13\..*?)\//')

echo addr=$addr

sudo -E snap remove microk8s --purge
sudo -E mkdir -p /var/snap/microk8s/common/ 

export http_proxy=
export https_proxy=

cat <<EOT > microk8s-launch-config.yaml
---
# 'version' is the semantic version of the configuration file format.
version: 0.1.0

extraSANs:
  - $addr

extraContainerdEnv:
  http_proxy: http://192.168.13.112:3128
  https_proxy: http://192.168.13.112:3128
  no_proxy: 127.0.0.1,192.168.0.0/16,172.16.0.0/12,10.0.0.0/8
  HTTP_PROXY: http://192.168.13.112:3128
  HTTPS_PROXY: http://192.168.13.112:3128
  NO_PROXY: 127.0.0.1,192.168.0.0/16,172.16.0.0/12,10.0.0.0/8

extraKubeAPIServerArgs:
  --bind-address: 0.0.0.0
  --advertise-address: $addr

extraKubeletArgs:
  --node-ip: $addr

# extraKubeProxyArgs:
#   --nodeport-addresses: $addr
#   --bind-address: 0.0.0.0

EOT

sudo -E cp microk8s-launch-config.yaml /var/snap/microk8s/common/.microk8s.yaml 
sudo -E snap install microk8s --classic
sudo -E /snap/bin/microk8s status -w
