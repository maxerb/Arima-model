"""Explore (D-21): time each step of the membership estimation."""
import time
from arima_snb import classify
t = time.time()
keys = classify.leaf_keys(); print("keys", len(keys), round(time.time() - t), flush=True)
A, b, uk, cats = classify.build_system("origin", keys); print("system", A.shape, round(time.time() - t), flush=True)
