set -uex
cd $(dirname $0)
make -C stellar-globe
make -C react-stellar-globe
make -C react-draggable-dialog
make -C app node_modules
make -C app -j
make -C python-integration/python setup datamodel build base_python=python3
make -C python-integration/jupyterlab-extension setup build base_python=python3
make -C python-integration/jupyterlite setup build base_python=python3
