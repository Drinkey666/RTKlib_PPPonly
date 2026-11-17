"""Run existing 215 numerical/model regression checks with freshly rebuilt, unchanged core objects."""
from pathlib import Path
import subprocess,json
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'validation/observation_generation_2023_v1'
unit=OUT/'core_tests';unit.mkdir(exist_ok=True)
(unit/'ppp_estimator_under_test.c').write_bytes((ROOT/'src/ppp.c').read_bytes())
names=['rtkcmn','trace','preceph','ephemeris','ionex','sbas','sofa','tides','pntpos','ppp_ar','ppp_position','smartphone_ppp_config','ppp_innovation_diag']
objects=' '.join(f'"{OUT/"pc_obj"/(n+".obj")}"' for n in names)
flags='/nologo /utf-8 /O2 /Gy /MD /D_CRT_SECURE_NO_WARNINGS /DENAGLO /DWIN32 /DTRACE /DNDEBUG /DDLL /D_LIB /Isrc'
dev='E:/Program Files/Microsoft Visual Studio/2022/Professional/Common7/Tools/VsDevCmd.bat'
results={}
for suite in ['phase1','phase2','physical_atmosphere','rapppid_estimator','covariance_fix']:
 ref=' tests/filter_reference_97a57a9.c' if suite in ['phase1','phase2'] else ''
 cmd=f'@echo off\ncall "{dev}" -arch=x64 -host_arch=x64 >nul\ncl {flags} /I"{unit}" /Fe"{unit/(suite+".exe")}" /Fo"{unit.as_posix()}/" tests/{suite}_regression.c{ref} {objects} /link /OPT:REF winmm.lib ws2_32.lib\n'
 (unit/(suite+'.cmd')).write_text(cmd,encoding='ascii')
 r=subprocess.run(['cmd','/c',str(unit/(suite+'.cmd'))],cwd=ROOT,capture_output=True)
 (unit/(suite+'.build.log')).write_bytes(r.stdout+r.stderr)
 assert r.returncode==0,f'{suite}: build failed; inspect log'
 r=subprocess.run([str(unit/(suite+'.exe'))],cwd=ROOT,capture_output=True)
 (unit/(suite+'.results.txt')).write_bytes(r.stdout+r.stderr)
 assert r.returncode==0,f'{suite}: regression failed; inspect log'
 results[suite]=r.stdout.decode(errors='replace').splitlines()[-1];print(suite,results[suite],flush=True)
(OUT/'core_test_results.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
