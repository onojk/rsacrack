# RSAcrack

**RSAcrack**: Exploring a *conical coil model* of numbers and primes to visualize overlaps, factorization, and potential cryptographic implications.

---

## 📖 Overview

This project places the natural numbers along a 3D **conical spring (coil)**:

- A **full coil** contains all integers.
- A **prime coil** overlays only the prime numbers.
- At each prime, the two coils touch tangentially, forming intersection points.
- **Composite numbers** inherit structure from the primes beneath them.

👉 The goal: explore whether these **geometric overlaps** reveal shortcuts to **prime factorization** or alternative number-theoretic fingerprints.

---

## 🚀 Features

- 📐 **3D coil model** of natural numbers
- 🔍 Overlay of **prime coil vs. full coil**
- 📊 Visualization of tangent (prime) positions
- 🧮 **Divisor trail fingerprints** for distinguishing primes vs. composites
- 📑 Whitepaper included: [`whitepaper/rsacrack_whitepaper.pdf`](whitepaper/rsacrack_whitepaper.pdf)

---

## 🛠 Usage

Clone and set up:

```bash
git clone https://github.com/onojk/rsacrack.git
cd rsacrack
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

Single Number Trail

Compute and visualize the divisor trail for a number:

python trail_length.py 97 --plot
# -> writes trail_97_prime.png

Range Comparison

Scan a range and export a CSV of "trail excess":

python trail_compare.py 2 200
# -> writes trail_excess.csv

📊 Divisor-Trail Fingerprint

Define a conical coil C(t)C(t).
For nn, let D(n)={d∣n}D(n)={d∣n} sorted.

    Trail length:
    L(n)=∑i∥C(di+1)−C(di)∥
    L(n)=i∑​∥C(di+1​)−C(di​)∥

    Chord:
    Chord(n)=∥C(n)−C(1)∥
    Chord(n)=∥C(n)−C(1)∥

    Excess:
    E(n)=L(n)−Chord(n)
    E(n)=L(n)−Chord(n)

Properties:

    Prime p⇒D(p)={1,p}⇒E(p)=0p⇒D(p)={1,p}⇒E(p)=0
    (shortest possible trail).

    Composite n⇒E(n)>0n⇒E(n)>0.

Thus, E(n)E(n) acts as a fingerprint:
zero excess → prime, positive excess → composite.
🖼 Visuals

Prime (n=97)

Composite (n=98)
trail_98_composite
🔒 Security & Ethical Disclaimer

This project is purely educational and experimental.

    Only explores toy factorizations (small semiprimes, 32–64 bits).

    Not capable of factoring real cryptographic keys (RSA keys in practice are 2048+ bits).

    The purpose is to study mathematical patterns and visualization, not to attack real systems.

    Please use responsibly: attempting to crack real encryption without permission is illegal and unethical.

🔮 Next Steps

    Sweep larger ranges (e.g. up to n=10,000n=10,000) to study excess patterns.

    Explore scaling laws of E(n)E(n) for semiprimes.

    Compare with alternative coil parametrizations (logarithmic, Archimedean, etc.).

    Investigate connections to known prime-detecting functions.
### Classify & fingerprint
```bash
python coil_classifier.py 91 --signature
# prints class, factors, coil footprint (d1,d2,d3), and two signatures:
# - geometry-aware (depends on r0, alpha, beta, L)
# - geometry-invariant (depends only on factor pair)
