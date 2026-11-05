# Agentcast: one command per job. Needs the EE Workcenter (`workcenter doctor`).
VERSION ?= v0.1
BOARDS := hardware/$(VERSION)/main hardware/$(VERSION)/micbar
PY := $(shell [ -x /opt/workcenters/ee/venv/bin/python ] && echo /opt/workcenters/ee/venv/bin/python || echo python3)

.PHONY: design gates lint verify render

design:
	python3 hardware/$(VERSION)/library/gen_library.py
	set -e; for b in $(BOARDS); do workcenter design $(CURDIR)/$$b/design.py --route; done

gates:
	set -e; for b in $(BOARDS); do workcenter gates $(CURDIR)/$$b; done

render:
	set -e; for b in $(BOARDS); do workcenter render $(CURDIR)/$$b --views all; done

lint:
	$(PY) -m py_compile hardware/$(VERSION)/library/gen_library.py $(foreach b,$(BOARDS),$(b)/design.py)
	@if $(PY) -m ruff --version >/dev/null 2>&1; then $(PY) -m ruff check --line-length 120 hardware/$(VERSION); else echo "lint: ruff not installed, byte-compile only"; fi

verify: lint gates
	@echo "VERIFY GREEN"
