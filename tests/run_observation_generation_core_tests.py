"""Run the native PPP core regressions with a single set of x64 objects."""

import argparse
import json
import os
from pathlib import Path
import subprocess
from tempfile import mkdtemp


ROOT = Path(__file__).resolve().parents[1]
RELEASE_OBJECTS = ROOT / "build/PPP_only/x64/Release"
HISTORICAL_OBJECTS = ROOT / "validation/observation_generation_2023_v1/pc_obj"
DEV = Path("E:/Program Files/Microsoft Visual Studio/2022/Professional/Common7/Tools/VsDevCmd.bat")
FLAGS = (
    "/nologo /utf-8 /O2 /Gy /MD /D_CRT_SECURE_NO_WARNINGS "
    "/D_WINSOCK_DEPRECATED_NO_WARNINGS /DENAGLO /DWIN32 /DTRACE /DNDEBUG /DDLL /D_LIB"
)
CORE_SUITES = ("phase1", "phase2", "physical_atmosphere", "rapppid_estimator", "covariance_fix")
CORE_OBJECTS = (
    "rtkcmn", "trace", "preceph", "ephemeris", "ionex", "sofa", "tides", "pntpos",
    "ppp_position", "smartphone_ppp_config", "ppp_innovation_diag",
)
OBSERVATION_OBJECTS = ("rtkcmn", "trace", "gnss_adapter", "gnss_signal_policy")


def run_suite(suite, names, work, object_dir, arguments=()):
    sources = [ROOT / "tests" / (suite + "_regression.c")]
    if suite in ("phase1", "phase2"):
        sources.append(ROOT / "tests/filter_reference_97a57a9.c")
    objects = [object_dir / (name + ".obj") for name in names]
    for path in objects:
        if not path.is_file():
            raise FileNotFoundError(path)
    inputs = " ".join(f'"{path}"' for path in (*sources, *objects))
    executable = work / (suite + ".exe")
    batch = work / (suite + ".cmd")
    flags = FLAGS
    if suite == "observation_generation" and object_dir != HISTORICAL_OBJECTS.resolve():
        flags += " /DPPP_USE_CURRENT_RAW_PARSER"
    batch.write_text(
        f'@echo off\ncall "{DEV}" -arch=x64 -host_arch=x64 >nul\n'
        'if errorlevel 1 exit /b 1\n'
        f'cl {flags} /I"{ROOT / "src"}" /I"{work}" /Fe"{executable}" '
        f'/Fo"{work.as_posix()}/" {inputs} /link /OPT:REF winmm.lib ws2_32.lib '
        'comdlg32.lib user32.lib gdi32.lib\n',
        encoding="ascii",
    )
    environment = dict(os.environ, TEMP=str(work), TMP=str(work))
    result = subprocess.run(["cmd.exe", "/d", "/c", str(batch)], cwd=work, env=environment, capture_output=True)
    build_log = work / (suite + ".build.log")
    build_log.write_bytes(result.stdout + result.stderr)
    if result.returncode:
        raise RuntimeError(f"{suite}: build failed: {build_log}")
    result = subprocess.run([str(executable), *arguments], cwd=work, env=environment, capture_output=True)
    results_path = work / (suite + ".results.txt")
    results_path.write_bytes(result.stdout + result.stderr)
    if result.returncode:
        raise RuntimeError(f"{suite}: regression failed: {results_path}")
    summary = result.stdout.decode(errors="replace").splitlines()[-1]
    print(suite, summary, flush=True)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--objects", type=Path, default=RELEASE_OBJECTS,
                        help="Directory of the x64 object files (default: current Release build)")
    parser.add_argument("--output", type=Path, help="New output directory under tmp/")
    parser.add_argument("--extended", action="store_true",
                        help="Also run observation generation and the four file-PPP specialty suites")
    parser.add_argument("--antex", type=Path, help="Optional ANTEX for the B1C calibration checks")
    args = parser.parse_args()
    object_dir = args.objects.resolve(strict=True)
    tmp = (ROOT / "tmp").resolve()
    if args.output:
        work = args.output.resolve()
        if not work.is_relative_to(tmp) or work == tmp:
            parser.error("--output must be a new subdirectory of tmp/")
        work.mkdir(parents=True)
    else:
        tmp.mkdir(exist_ok=True)
        work = Path(mkdtemp(prefix="observation_generation_tests_", dir=tmp))
    for name in ("phase1", "phase2", "product_check"):
        (work / "validation" / name).mkdir(parents=True)
    (work / "ppp_estimator_under_test.c").write_bytes((ROOT / "src/ppp.c").read_bytes())

    if args.extended and object_dir != HISTORICAL_OBJECTS.resolve():
        replay_source = (ROOT / "src/gnss_replay.c").read_bytes()
        start = replay_source.index(b"static int split_csv(")
        end = replay_source.index(b"static void normalize_clock(", start)
        (work / "production_parser.h").write_bytes(replay_source[start:end])

    # The archived clock-generation objects still contain calls to these modules.
    core_objects = CORE_OBJECTS
    if object_dir == HISTORICAL_OBJECTS.resolve():
        core_objects += ("sbas", "ppp_ar")
    suites = {name: core_objects for name in CORE_SUITES}
    if args.extended:
        suites.update(
            observation_generation=OBSERVATION_OBJECTS,
            verified_profile=core_objects,
            b1c_integration=core_objects + ("gnss_adapter", "gnss_signal_policy"),
            b2b_exclusion=core_objects,
            product_check=core_objects + (
                "ppp_product_check", "rinex", "gnss_adapter", "gnss_signal_policy", "gnss_replay", "pc_file_picker",
            ),
        )
    antex = (str(args.antex.resolve(strict=True)),) if args.antex else ()
    print(f"Objects: {object_dir}\nResults: {work}", flush=True)
    results = {}
    try:
        for suite, names in suites.items():
            results[suite] = run_suite(suite, names, work, object_dir, antex if suite == "b1c_integration" else ())
    finally:
        (work / "core_test_results.json").write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
