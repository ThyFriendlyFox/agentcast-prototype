# Configuration

| Option | Where | Default | Effect |
|---|---|---|---|
| `VERSION` | `make` variable | `v0.1` | The hardware version `make design`, `make gates` and `make verify` act on. |
| `dtparam=ant1` / `ant2` | CM5 `config.txt` | `ant1` | Internal PCB antenna or U.FL (CM5 datasheet 2.2). v0.1 keeps the board clear under the internal antenna. |
| I2S0 pins | CM5 device tree | none | GPIO18-20 and GPIO22 in alt a2 for the mic bar (pin plan in the v0.1 README). |
