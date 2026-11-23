# Virtual environment fallback

Use this only when uv is unavailable. Reuse the project's `.venv` if present;
avoid installing into system Python. Run from the project root:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r tools/requirements.txt ruff==0.14.4 ty==0.0.107
.venv/bin/ty check tools --error-on-warning
.venv/bin/python -m ruff check --no-cache tools
.venv/bin/python -m ruff format --no-cache --check tools
.venv/bin/python -B -W error -m unittest discover -s tools -p 'test_*.py'
.venv/bin/python -B tools/validate.py
```

Choose checks according to the entrypoint's workflow; site validation is needed
only when site inputs or rules change. To format requested files, run
`.venv/bin/python -m ruff format --no-cache` with those paths.
On Windows use `.venv\Scripts\python.exe` and `.venv\Scripts\ty.exe`.
The standalone local link checker and its tests do not need third-party packages:

```sh
python3 tools/check_links.py
python3 -B -W error -m unittest discover -s tools -p 'test_check_links.py'
```
