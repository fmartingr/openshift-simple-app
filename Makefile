setup:
	$$(pyenv which python) -m venv .venv
	. .venv/bin/activate && pip install -r requirements-dev.txt
