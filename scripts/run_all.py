# -*- coding: utf-8 -*-
"""
Runs the complete pipeline, from the raw source files to every table, figure
and number reported in the manuscript and the Supplementary Material.

Usage:
    python scripts/run_all.py

Environment variables (optional):
    REPRO_OUTPUTS  output folder (default: ./outputs)
    REPRO_RAW      folder with the raw sources (default: ./data/raw)
    PY38           path to a Python 3.8 interpreter with differences 0.1.2
                   (requirements-py38.txt). Step 06b reproduces the earlier
                   software version; without PY38 the reference cell tables in
                   results/software/ are copied instead and a notice is printed.
"""
import os, sys, shutil, subprocess, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUTPUTS = os.environ.get("REPRO_OUTPUTS", os.path.join(ROOT, "outputs"))
PASOS = ["00_verify_sources.py", "01_build_panel.py", "02_treatment_dating.py",
         "03_master_table.py", "04_primary_estimates.py", "05_specifications_dating.py",
         "06a_export_panels.py", "06b_differences_012_py38.py",
         "06c_compare_implementations.py", "07_overlap.py", "08_inference_validity.py",
         "09_evidence_table.py", "10_operational_coding.py", "11_operational_sensitivity.py",
         "12_manuscript_numbers.py", "13_figures.py", "14_supplementary.py"]


def main():
    env = dict(os.environ, REPRO_OUTPUTS=OUTPUTS, PYTHONIOENCODING="utf-8")
    t0 = time.time()
    for paso in PASOS:
        py = sys.executable
        if paso.startswith("06b"):
            py = os.environ.get("PY38")
            if not py:
                dst = os.path.join(OUTPUTS, "results", "software")
                os.makedirs(dst, exist_ok=True)
                for f in os.listdir(os.path.join(ROOT, "results", "software")):
                    if f.startswith(("celdas_v012_", "evento_v012_")):
                        shutil.copy(os.path.join(ROOT, "results", "software", f), dst)
                print("[06b] PY38 not set: reference differences-0.1.2 cell tables copied "
                      "from results/software/ (set PY38 to recompute them)")
                continue
        print("\n=== %s ===" % paso, flush=True)
        r = subprocess.run([py, os.path.join(HERE, paso)], cwd=HERE, env=env)
        if r.returncode != 0:
            sys.exit("step %s failed (exit %d)" % (paso, r.returncode))
    print("\nPipeline finished in %.1f min. Outputs in %s" % ((time.time() - t0) / 60, OUTPUTS))


if __name__ == "__main__":
    main()
