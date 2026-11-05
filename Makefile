# Agentcast: one command per job. Needs the EE Workcenter (`workcenter doctor`).
VERSION ?= v0.3
BOARDS := $(patsubst %/,%,$(dir $(wildcard hardware/$(VERSION)/*/design.py)))
PY := $(shell [ -x /opt/workcenters/ee/venv/bin/python ] && echo /opt/workcenters/ee/venv/bin/python || echo python3)

.PHONY: design gates lint verify render fab cm5-model assembly

design:
	python3 hardware/$(VERSION)/library/gen_library.py
	set -e; for b in $(BOARDS); do workcenter design $(CURDIR)/$$b/design.py --route; done

gates:
	set -e; for b in $(BOARDS); do workcenter gates $(CURDIR)/$$b; done

# Every view; --strict fails on a part drawn without a 3D body.
render:
	set -e; for b in $(BOARDS); do workcenter render $(CURDIR)/$$b --views all --strict; done

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

# Raspberry Pi's CM5 3D model (RP-007222-DD-2), for assembly pictures. Not kept in git.
CM5_STEP_URL := https://pip-assets.raspberrypi.com/categories/1096-design-files/documents/RP-007222-DD-2-rpi-cm5%203D_STEP.zip
cm5-model:
	set -e; for b in $(BOARDS); do \
	  [ -s $$b/models/cm5.step ] && continue; \
	  curl -fsSL -o $$b/models/cm5-step.zip "$(CM5_STEP_URL)"; \
	  unzip -p $$b/models/cm5-step.zip '*.step' > $$b/models/cm5.step; \
	done

# The board with the CM5 on it, built into build/assembly/ (the board's own files stay as they are).
assembly: cm5-model
	set -e; for b in $(BOARDS); do \
	  mkdir -p $(CURDIR)/$$b/build/assembly/models && cp $$b/models/*.wrl $$b/models/cm5.step $(CURDIR)/$$b/build/assembly/models/; \
	  AGENTCAST_ASSEMBLY=1 workcenter design $(CURDIR)/$$b/design.py --route --out $(CURDIR)/$$b/build/assembly; \
	  workcenter render $(CURDIR)/$$b/build/assembly --views 3d,spin; \
	done

lint:
	$(PY) -m py_compile hardware/$(VERSION)/library/gen_library.py $(foreach b,$(BOARDS),$(b)/design.py)
	@if $(PY) -m ruff --version >/dev/null 2>&1; then $(PY) -m ruff check --line-length 120 hardware/$(VERSION); else echo "lint: ruff not installed, byte-compile only"; fi

verify: lint gates
	@echo "VERIFY GREEN"
