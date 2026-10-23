.PHONY: setup data train web run worker test
setup:
	python3.12 -m venv .venv
	.venv/bin/pip install -r requirements.txt
	cd web && npm ci
data:
	.venv/bin/python scripts/fetch_data.py
	.venv/bin/python scripts/prepare.py
train:
	OMP_NUM_THREADS=2 .venv/bin/python scripts/train.py
web:
	cd web && npm run build
run:
	.venv/bin/python -m uvicorn concord.api:app --host 127.0.0.1 --port 8765
worker:
	.venv/bin/python -m concord.worker
test:
	.venv/bin/python -m pytest -q
	cd web && npm run build
