# -*- coding: utf-8 -*-
"""Writes checksums/manifest_sha256.csv with the SHA-256 of every package file
(excluding .git, outputs/ except the verification report, and caches).
Usage:  python scripts/generate_manifest.py"""
import os, csv, hashlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
filas = []
for raiz, dirs, fs in os.walk(ROOT):
    dirs[:] = [d for d in dirs if d not in (".git", "__pycache__")]
    for f in sorted(fs):
        p = os.path.join(raiz, f)
        rel = os.path.relpath(p, ROOT).replace("\\", "/")
        if rel.startswith("checksums/") or (rel.startswith("outputs/") and "reproducibility_check_report" not in rel):
            continue
        if rel.startswith(("data/raw/dsp/", "data/raw/vdem/")) and rel.endswith(".csv"):
            continue
        if rel in ("results/software/panel_corregida.csv", "results/software/panel_enviada.csv"):
            continue
        h = hashlib.sha256(open(p, "rb").read()).hexdigest()
        filas.append([rel, os.path.getsize(p), h])
os.makedirs(os.path.join(ROOT, "checksums"), exist_ok=True)
with open(os.path.join(ROOT, "checksums", "manifest_sha256.csv"), "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh); w.writerow(["path", "bytes", "sha256"]); w.writerows(sorted(filas))
print("%d files" % len(filas))
