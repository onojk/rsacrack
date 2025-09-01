#!/usr/bin/env python3
import sys
sys.path.insert(0, '/home/onojk123_gmail_com/rsacrack')
from rsacrack.pipeline_smart import factor_smart

# Test the two numbers
n1 = 1022117
n2 = 100160063

print(f"Testing {n1}...")
result1 = factor_smart(n1, 9000)
print(f"Result: {result1}")

print(f"\nTesting {n2}...")
result2 = factor_smart(n2, 9000)
print(f"Result: {result2}")
