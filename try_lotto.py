from lotto_factor import factor_lotto_64

# Known semiprime (easy-ish)
p, q = 1000003, 1000033
n = p*q

print("N =", n)
print("Trying lotto (budget 600 ms)...")
res = factor_lotto_64(n, budget_ms=600)
print("Result:", res)

# Harder: change budget or feed different N's as needed.
