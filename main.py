#!/usr/bin/env python3

import math
import matplotlib.pyplot as plt
import numpy as np

def is_prime(n: int) -> bool:
    """Check if n is prime."""
    if n < 2:
        return False
    if n == 2:
        return True
    if n % 2 == 0:
        return False
    for i in range(3, int(math.sqrt(n)) + 1, 2):
        if n % i == 0:
            return False
    return True

def generate_coil(limit=200, step=1):
    """Generate coordinates of the number coil (spiral)."""
    t = np.linspace(0, limit, limit*10)
    x = t * np.cos(step * t)
    y = t * np.sin(step * t)
    return x, y

def plot_primes(limit=200):
    """Overlay primes as dots on the number coil."""
    x, y = generate_coil(limit)
    plt.figure(figsize=(8,8))
    plt.plot(x, y, alpha=0.3, label="All Numbers Coil")

    # Overlay primes
    primes = [n for n in range(limit) if is_prime(n)]
    for p in primes:
        px = p * math.cos(p)
        py = p * math.sin(p)
        plt.scatter(px, py, color="red", s=20)

    plt.title("RSAcrack: Prime Coil Visualization")
    plt.axis("equal")
    plt.legend()
    plt.show()

if __name__ == "__main__":
    plot_primes(200)
