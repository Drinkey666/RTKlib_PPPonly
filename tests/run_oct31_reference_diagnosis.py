"""Repeat two fixed-clock baselines without feeding evaluation coordinates to PPP."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import csv, gzip, hashlib, json, os, shutil, subprocess, sys, time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from ppp_preset import environment, PROFILE

DATA = Path('E:/RTKLIB_Data/10.31')
OUT = ROOT / 'validation/oct31_reference_diagnosis_v1'
CONFIG = DATA / 'results_B_verified_fixed_clock/configuration.json'
EXE = ROOT / 'validation/observation_generation_2023_v1/pc_build/PPP_only.exe'
CASES = {
    'k70': (DATA / 'original/RawData_20261031_101334.txt',
            DATA / 'results_B_verified_fixed_clock/continuous_full/solution.csv'),
    'iq': (DATA / 'vivo_V2507A_file_ppp/RawData_20261031_101333.txt',
           DATA / 'vivo_V2507A_file_ppp/RawData_20261031_101333/solution.csv'),
}

def sha(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()

def save(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')

def replay(case):
    config = json.loads(CONFIG.read_text(encoding='utf-8'))
    files = {k: Path(v) for k, v in config['files'].items()}
    assert sha(EXE) == config['executable_sha256']
    assert all(sha(p) == config['file_sha256'][k] for k, p in files.items())
    files['TXT'] = CASES[case][0]
    folder = OUT / case
    folder.mkdir(parents=True, exist_ok=False)
    solution = folder / 'solution.csv'
    command = [str(EXE), '--source', 'txt-fast', '--no-gui']
    env = environment(os.environ, files)
    env.update(RTK_PPP_OUTPUT=str(solution), RTK_PPP_TRACE=str(folder / 'solution.trace'),
               RTK_PPP_TRACE_LEVEL='2')
    receipt = dict(case=case, executable=str(EXE), executable_sha256=sha(EXE),
                   profile=PROFILE, inputs={k: dict(path=str(p), sha256=sha(p)) for k,p in files.items()},
                   command=command, reference_used_in_filter=False,
                   cached_solution=str(CASES[case][1]), cached_solution_sha256=sha(CASES[case][1]))
    save(folder / 'run.json', receipt)
    with (folder / 'preflight.log').open('wb') as log:
        check = subprocess.run(command + ['--check-files'], cwd=ROOT, env=env,
                               stdout=log, stderr=subprocess.STDOUT)
    receipt['preflight_returncode'] = check.returncode
    save(folder / 'run.json', receipt)
    if check.returncode:
        raise RuntimeError(f'{case}: preflight failed')
    started = time.monotonic()
    print(f'{case}: preflight passed; replay started', flush=True)
    with (folder / 'console.log').open('wb') as log:
        result = subprocess.run(command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
    receipt.update(returncode=result.returncode, wall_seconds=time.monotonic()-started)
    save(folder / 'run.json', receipt)
    if result.returncode:
        raise RuntimeError(f'{case}: replay failed')
    with solution.open() as a, CASES[case][1].open() as b:
        actual, expected = [list(csv.DictReader(f)) for f in (a, b)]
    assert len(actual) == len(expected) == 3710
    mismatches = [(i+1,k) for i,(a,b) in enumerate(zip(actual,expected))
                  for k in a if k != 'processing_ms' and a[k] != b[k]]
    assert not mismatches, mismatches[:10]
    receipt.update(completed=True, epochs=len(actual), cached_fields_exact_except_processing_ms=True,
                   solution_sha256=sha(solution))
    receipt['compressed_logs'] = {}
    for path in [folder/'solution.trace', Path(str(solution)+'.stat'), Path(str(solution)+'.obs.csv')]:
        digest = sha(path)
        target = Path(str(path)+'.gz')
        with path.open('rb') as src, gzip.open(target,'wb',compresslevel=5) as dst:
            shutil.copyfileobj(src,dst)
        with gzip.open(target,'rb') as f:
            assert hashlib.file_digest(f,'sha256').hexdigest() == digest
        receipt['compressed_logs'][path.name] = dict(path=str(target), uncompressed_sha256=digest)
        path.unlink()  # Only this run's verified, losslessly compressed output.
    assert all(sha(p) == receipt['inputs'][k]['sha256'] for k,p in files.items())
    assert sha(CASES[case][1]) == receipt['cached_solution_sha256']
    save(folder/'run.json',receipt)
    print(f'{case}: {len(actual)} epochs; exact cached-field reproduction; {receipt["wall_seconds"]:.1f}s',flush=True)

if __name__ == '__main__':
    OUT.mkdir(parents=True, exist_ok=False)
    save(OUT/'reference.json', json.loads((DATA/'reference_points_20261107.json').read_text(encoding='utf-8')))
    save(OUT/'source_identity.json', dict(script_sha256=sha(__file__),
         note='Fresh user-requested replay; same fixed-clock baseline, evaluation points never enter the filter.'))
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(replay, CASES))
