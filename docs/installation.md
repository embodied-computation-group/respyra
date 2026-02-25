# Installation

## Requirements

- **Python 3.10** — PsychoPy does not yet support Python 3.11+
- **Vernier Go Direct Respiration Belt** (GDX-RB) — for hardware-dependent features

## From PyPI

```bash
pip install respyra
```

For post-session visualization (adds pandas and matplotlib):

```bash
pip install "respyra[vis]"
```

## Development install

```bash
git clone https://github.com/embodied-computation-group/respyra.git
cd respyra
py -3.10 -m venv .venv       # Windows
# python3.10 -m venv .venv   # macOS / Linux
```

Activate the virtual environment:

```bash
# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

Install in editable mode:

```bash
pip install -e ".[vis]"
```

## Verify the installation

```bash
python -c "import respyra; print(respyra.__version__)"
```

## Platform notes

### Windows (BLE)

The Vernier belt's BLE scanner ([Bleak](https://github.com/hbldh/bleak)) requires the main thread with COM in MTA mode. PsychoPy's graphics backend sets COM to STA on import. respyra handles this by connecting the belt **before** importing PsychoPy — no manual workaround is needed when using the provided scripts.

If you encounter BLE failures, try USB as a fallback (connect the belt with the included USB cable).

### Linux

USB access requires udev rules. Create `/etc/udev/rules.d/99-godirect.rules`:

```
SUBSYSTEM=="usb", ATTR{idVendor}=="08f7", MODE="0666"
```

Then reload:

```bash
sudo udevadm control --reload-rules && sudo udevadm trigger
```

### macOS

Both BLE and USB work out of the box.
