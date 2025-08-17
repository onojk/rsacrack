rsacrack/
├── README.md
├── LICENSE
├── requirements.txt
├── coil_model.py
├── prime_overlay.py
├── factor_test.py
├── diagrams/
│   └── .gitkeep
├── whitepaper/
│   └── rsacrack_whitepaper.pdf
└── .gitignore

📄 README.md

# RSAcrack

RSAcrack: Exploring a conical spring (coil) model of numbers and primes to visualize overlaps, factorization, and potential cryptographic implications.

## Overview
This project models numbers along a conical coil, with primes forming a tangent coil that intersects at prime positions.  
Composite numbers inherit structure from prime overlaps beneath their location.  
The goal is to study whether these geometric relationships reveal shortcuts to **prime factorization**.

## Features
- 3D coil model of natural numbers
- Overlay of prime coil vs. full coil
- Visualization of tangent points (prime positions)
- Experimental factorization methods
- Whitepaper included

## Quick Start
```bash
git clone https://github.com/YOURNAME/rsacrack.git
cd rsacrack
pip install -r requirements.txt
python coil_model.py

Status

Coil equation formalized

Visualizations of primes vs. all numbers

Factorization prototype

    Benchmark against RSA key sizes

Disclaimer

This project is experimental research.
It is not a proven method for breaking RSA cryptography — use responsibly.


---

### 📄 `requirements.txt`
```txt
matplotlib
numpy
sympy

📄 .gitignore

__pycache__/
*.pyc
*.pyo
*.png
*.pdf
*.DS_Store

