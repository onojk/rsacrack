from cprime_runner import factor_uint64

def demo():
    p, q = 1000003, 1000033
    n = p*q
    print("N =", n)
    res = factor_uint64(n, iters=200_000, restarts=64)
    print("factor_uint64 ->", res)

if __name__ == "__main__":
    demo()
