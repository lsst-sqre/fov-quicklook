set -v

frontend_port=19500
coordinator_port=19501

for port in {19500..19502} ; do
  /usr/sbin/lsof -i :$port | sed 1d | perl -anle 'print $F[1]' | xargs -r kill
done

export http_proxy=
export HTTP_PROXY=
export QUICKLOOK_environment=test
export QUICKLOOK_coordinator_base_url=http://localhost:$coordinator_port
export QUICKLOOK_frontend_port=$frontend_port
export QUICKLOOK_s3_repository='{"access_key": "quicklook", "secret_key": "password", "endpoint": "192.168.13.201:9000", "secure": false, "bucket": "quicklook-repository"}'
export QUICKLOOK_s3_tile='{"access_key": "quicklook", "secret_key": "password", "endpoint": "192.168.13.201:9000", "secure": false, "bucket": "quicklook-tile"}'
export QUICKLOOK_timeit_log_level=DEBUG
export QUICKLOOK_hearbeat_interval=5
export QUICKLOOK_dev_reload=true
export QUICKLOOK_dev_ccd_limit=5
export QUICKLOOK_frontend_assets_dir=../frontend/app/dist
export WATCHFILES_IGNORE_PERMISSION_DENIED=1

QUICKLOOK_dev_log_prefix="[frontend]   " ./.venv/bin/python -m quicklook.frontend.api &
frontend_pid=$!

QUICKLOOK_dev_log_prefix="[coodinator] " ./.venv/bin/python -m quicklook.coordinator.api &
coodinator_pid=$!

while ! curl http://127.0.0.1:$coordinator_port/healthz ; do
  sleep 1
done
echo "Coordinator is ready"

QUICKLOOK_dev_log_prefix="[generator1]  " QUICKLOOK_generator_port=19502 ./.venv/bin/python -m quicklook.generator.api &
generator_pid1=$!
QUICKLOOK_dev_log_prefix="[generator2]  " QUICKLOOK_generator_port=19503 ./.venv/bin/python -m quicklook.generator.api &
generator_pid2=$!

wait $frontend_pid $coodinator_pid $generator_pid1 $generator_pid2