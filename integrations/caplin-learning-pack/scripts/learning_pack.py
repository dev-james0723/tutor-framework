#!/usr/bin/env python3
"""Thin installed entrypoint; all implementation stays in tutor-framework."""
from __future__ import annotations
import json
import os
import subprocess
import sys
from pathlib import Path


def main(argv=None):
    args=list(sys.argv[1:] if argv is None else argv)
    root=Path(__file__).resolve().parents[1]
    config_file=root/'learning-pack-runtime.json'
    if not config_file.is_file():
        print('Caplin Learning Pack runtime is not configured. Run the repository deployment tool.',file=sys.stderr)
        return 2
    try:
        config=json.loads(config_file.read_text())
        if set(config)-{'repository','python','export_runtime','release_commit'}:
            raise ValueError('unknown local runtime keys')
        repository=Path(config['repository']).expanduser().resolve(strict=True)
        interpreter=Path(config['python']).expanduser().absolute()
        if not interpreter.is_file() or not os.access(interpreter,os.X_OK):
            raise ValueError('configured Python interpreter is missing or not executable')
        if not (repository/'src/tutor_framework/domains/music/lesson/learning_pack/__main__.py').is_file():
            raise ValueError('authoritative Learning Pack module is missing')
        export_setting=config.get('export_runtime')
        # Text-only installations may run doctor without a configured PDF renderer.
        if export_setting is not None and args and args[0] in {'doctor','build'}:
            if '--runtime' not in args and '--no-pdf' not in args:
                export=Path(export_setting).expanduser().resolve(strict=True)
                args += ['--runtime',str(export)]
        command=[str(interpreter),'-m','tutor_framework.domains.music.lesson.learning_pack',*args]
        environment={**os.environ,'PYTHONPATH':str(repository/'src'),'PYTHONDONTWRITEBYTECODE':'1'}
        return subprocess.run(command,env=environment,check=False).returncode
    except (OSError,ValueError,TypeError,KeyError) as error:
        print('Caplin Learning Pack blocked: '+str(error),file=sys.stderr)
        return 2


if __name__=='__main__':
    raise SystemExit(main())
