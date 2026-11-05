# Agentcast: one command per job. Needs the EE Workcenter (`workcenter doctor`).
VERSION ?= v0.2
BOARDS := $(patsubst %/,%,$(dir $(wildcard hardware/$(VERSION)/*/design.py)))
PY := $(shell [ -x /opt/workcenters/ee/venv/bin/python ] && echo /opt/workcenters/ee/venv/bin/python || echo python3)

.PHONY: design gates lint verify render fab

design:
	python3 hardware/$(VERSION)/library/gen_library.py
	set -e; for b in $(BOARDS); do workcenter design $(CURDIR)/$$b/design.py --route; done

gates:
	set -e; for b in $(BOARDS); do workcenter gates $(CURDIR)/$$b; done

render:
	set -e; for b in $(BOARDS); do workcenter render $(CURDIR)/$$b --views all; done

# The EXPORT gate's output (Gerbers, drill, BOM, schematic PDF) plus a pick-and-place file, copied
# into each board's fab/ for the board house. Runs the gates first: no files from a red board.
# Files are overwritten in place; delete fab/ by hand if a layer was dropped.
fab: gates
	set -e; for b in $(BOARDS); do \
	  mkdir -p $$b/fab && cp -r $$b/build/fab/. $$b/fab/; \
	  pcb=$$(ls $$b/*.kicad_pcb); \
	  kicad-cli pcb export pos --format csv --units mm --side both \
	    --output $$b/fab/$$(basename $$pcb .kicad_pcb)-pos.csv $$pcb; \
	done

lint:
	$(PY) -m py_compile hardware/$(VERSION)/library/gen_library.py $(foreach b,$(BOARDS),$(b)/design.py)
	@if $(PY) -m ruff --version >/dev/null 2>&1; then $(PY) -m ruff check --line-length 120 hardware/$(VERSION); else echo "lint: ruff not installed, byte-compile only"; fi

verify: lint gates
	@echo "VERIFY GREEN"
