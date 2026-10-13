# -*- coding: utf-8 -*-
"""
Step 00 — checks that the raw source files are present and are exactly the
versions used in the study (SHA-256).

Usage:  python scripts/00_verify_sources.py
"""
import os, sys, hashlib
import common as rc

ESPERADO = {
    rc.AIGS_XLSX: "d36990124a364c49a3425a3aad8d93d667f3440286b0420d181f7d073600cdc2",
    rc.ZOTERO: "b8960cef4653c24e545fcb5a2969bd5f650b661d0b91cd95da2b347e7ed187f8",
    rc.DSP_CSV: "a931f3566a9433481fee131908f17c1789587a377a868950546227b78960afe8",
    rc.VDEM_CSV: "d65f32bacb7b358c58ca9c908424444170058fc283acb625f3a6bce74faa1994",
}


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main():
    mal = 0
    for p, h in ESPERADO.items():
        if not os.path.exists(p):
            print("MISSING  %s  (see data_access/source_datasets.md)" % p); mal += 1
            continue
        ok = sha256(p) == h
        print("%-8s %s" % ("OK" if ok else "MISMATCH", p))
        mal += not ok
    if mal:
        sys.exit("%d source file(s) missing or different from the versions used" % mal)


if __name__ == "__main__":
    main()
