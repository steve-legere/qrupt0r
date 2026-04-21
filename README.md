<p align="center">
  <img src="img/banner.png" alt="qrupt0r banner" width="500"/>
</p>

<p align="center">
  <b>:: dual-module QR generator ::</b>
</p>

## 🔍 Overview

**qrupt0r** is a Python commandline tool that combines two URLs or character strings into a single
*dual-module QR code*.  
These dual-module QR codes can produce **different decoding results depending on scan conditions** (e.g., distance,
resolution, or scanning method).

This project is designed for **security research, testing, and educational purposes**, particularly for evaluating how
QR code scanners and security systems handle ambiguous or adversarial inputs.

---

## 🧠 How it Works

qrupt0r generates two QR codes from user input, then merges them using a **module-level overlay technique**:

- The first QR code is used as the **base**
- The second QR code is embedded as **submodules**
- Submodules are only placed where the two QR codes differ

The result is a QR code that:

- Appears slightly different from typical QR codes
- May decode differently depending on scanning conditions

---

## ⚠️ Security Considerations

Dual-module QR codes highlight the gap between:

- **Human perception** (what you think you're scanning)
- **Machine interpretation** (what actually gets decoded)

This makes them useful for:

- Testing QR scanning reliability
- Evaluating email/web security products
- Researching computer vision edge cases
- Demonstrating QR-based evasion techniques in controlled environments

---

## 📦 Requirements

- Python **3.9+**
- Recommended: virtual environment (`venv`, `conda`, etc.)

### Dependencies

```text
pyfiglet~=1.0.4
qrcode~=8.2
typer~=0.24.1
pillow~=12.2.0
```

Install:

```shell
pip install -r requirements.txt
```

---

## ⚙️ CLI Options

Usage:

```text
qrupt0r.py [OPTIONS] PRIMARY_URL OVERLAY_URL
```

### Arguments

- `primary_url` → Base QR code URL
- `overlay_url` → Embedded QR code URL

### Optional Arguments

| Option              | Description                           | Default       |
|---------------------|---------------------------------------|---------------|
| `-b, --border`      | Border thickness (modules)            | `4`           |
| `--debug`           | Enable debug output                   | —             |
| `-e, --error-level` | Error correction (`L`, `M`, `Q`, `H`) | `L`           |
| `--force`           | Force output (may cause errors)       | —             |
| `-m, --module`      | Module size (pixels)                  | `29`          |
| `-o, --output`      | Output PNG file path                  | `qrupt0r.png` |
| `--silent`          | Suppress non-critical output          | —             |
| `-s, --submodule`   | Submodule size (pixels)               | `5`           |
| `--help`            | Show the help menu                    | —             |

---

## 🖼️ Examples

### Partial Difference (minor variation)

```shell
python qrupt0r.py -o example-partial.png https://www.example.com/3 https://www.example.com/5
```

### Full Difference (major variation)

```shell
python qrupt0r.py -o example-full.png https://www.example.com/3 https://www.example.com/4
```

<p align="center">
  <img src="img/example-partial.png" alt="Partial Difference Example" width="300" style="margin-right: 20px;" />
  <img src="img/example-full.png" alt="Full Difference Example" width="300" />
</p>

<p align="center">
  <sub>
    <b>Left:</b> Partial difference — inputs are similar, differences mostly in error correction.<br>
    <b>Right:</b> Full difference — inputs diverge significantly, resulting in extensive submodule embedding.
  </sub>
</p>



---

## 🔬 Use Cases

- QR code scanner robustness testing
- Email security gateway evaluation (QR phishing detection)
- Mobile device QR parsing analysis
- Research into visual vs decoded discrepancies
- Demonstrating limitations of static QR inspection

---

## 📚 Reference

Based on published research:

> Chou, K.-C., & Wang, R.-Z. (2024). Dual-Message QR Codes. Sensors, 24(10), 3055.
> https://doi.org/10.3390/s24103055

---

## Disclaimer

This project is provided for **educational and defensive security research purposes only**.

Users are responsible for ensuring their usage complies with applicable laws, regulations, and organizational policies.
