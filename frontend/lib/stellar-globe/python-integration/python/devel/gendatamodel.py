import contextlib
import json
import logging
import re
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Dict

from .extractschema import extractSchema
from .pycodemanipulate import replace_definition, replace_type_annotation


def main():
    logging.basicConfig(level=logging.INFO)

    tmp_dir = Path('./tmp/models')
    dest_dir = Path('./src/hscmap/models')
    app_schema = load_json_file(Path('../../app/jsonschema/public.json'))

    shutil.rmtree(tmp_dir, ignore_errors=True)

    with make_models_parallel() as make_model:
        for model_name in extractSchema(app_schema, ['ToApp'])['properties'].keys():
            schema = extractSchema(app_schema, ['ToApp', model_name])
            make_model(
                schema,
                tmp_dir / f'{model_name}.py',
                {'Model.type': f"type: Literal[{repr(model_name)}]"},
            )

        for model_name in extractSchema(app_schema, ['FromApp'])['properties'].keys():
            schema = extractSchema(app_schema, ['FromApp', model_name])
            make_model(
                schema,
                tmp_dir / 'frontend' / f'{model_name}.py',
                {'Model.type': f"type: Literal[{repr(model_name)}]"},
            )

        make_model(
            extractSchema(app_schema, ['StoreState']),
            tmp_dir / f'store.py',
        )

        action_names = extractSchema(app_schema, ['Actions'])['properties'].keys()

        for action_name in action_names:
            schema = extractSchema(app_schema, ['Actions', action_name])
            make_model(
                schema,
                tmp_dir / 'actions' / f'{action_name}.py',
                {'Model.type': f"type: Literal[{repr(action_name)}]"},
            )

    subprocess.check_call(['rsync', '-av', '--exclude=.gitignore', '--delete', f'{tmp_dir}/', dest_dir])
    run_bash('''find ./src/hscmap/models  -type d | grep -v __pycache__ | while read d; do touch $d/__init__.py; done''')
    shutil.rmtree(tmp_dir, ignore_errors=True)


@contextlib.contextmanager
def make_models_parallel():
    with ThreadPoolExecutor() as executor:

        def f(schema, outfile: Path, replace_map: Dict[str, str] = {}):
            def g():
                generate_datamodel(schema, outfile, replace_map)

            executor.submit(g)

        yield f


def generate_datamodel(schema, outfile: Path, replace_map: Dict[str, str] = {}):
    logging.info(f'Generating {outfile}...')
    try:
        codes = datamodel_codegen(schema)
        codes = replace_type_annotation(codes, 'NotRequired', 'Optional')
        for k, v in replace_map.items():
            codes = replace_definition(codes, k, v)
        codes = re.sub(r'^(from\s+__future__\s+import\s+annotations)', r'\1\nfrom typing import Optional, Literal, TypedDict', codes)
        codes = re.sub(r'^(from typing_extensions.*)', r'', codes, flags=re.MULTILINE)
        codes = re.sub(r'NotRequired', r'Optional', codes, flags=re.MULTILINE)

        outfile.parent.mkdir(parents=True, exist_ok=True)
        outfile.write_text(codes)
    except:
        import traceback

        traceback.print_exc()


def datamodel_codegen(schema):
    with \
        tempfile.NamedTemporaryFile('w') as input,\
        tempfile.NamedTemporaryFile('w') as output:
        input.write(json.dumps(schema))
        input.flush()
        p = subprocess.Popen(
            [
                f'{sys.prefix}/bin/datamodel-codegen',
                '--input-file-type',
                'jsonschema',
                '--input',
                input.name,
                '--output-model-type',
                'typing.TypedDict',
                '--output',
                output.name,
            ],
        )
        p.wait()
        assert p.returncode == 0
        codes = Path(output.name).read_text()
    return codes


def load_json_file(path: Path):
    return json.loads(path.read_text())


def run_bash(cmd: str):
    logging.info(f'Running {cmd}...')
    subprocess.check_call(['bash', '-c', cmd])


if __name__ == '__main__':
    main()
