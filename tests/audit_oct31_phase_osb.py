"""Verify whether BIA phase OSBs affect the exact Oct31 TXT executable.

Original products and production sources are read-only. Derived BIA removes
only L-type OSB records; unchanged C records and all metadata are retained.
"""
from concurrent.futures import ThreadPoolExecutor
from collections import Counter
from pathlib import Path
import csv, hashlib, json, os, re, subprocess, sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from ppp_preset import environment

BASE=ROOT/'validation/oct31_reference_diagnosis_v1'
OUT=ROOT/'validation/oct31_phase_osb_audit_v1'

def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def save(p,v):Path(p).write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')

def obs_type(line):
    t=line.split()
    if not t or t[0]!='OSB':return None
    return next((x for x in t[3:] if re.fullmatch(r'[CL][0-9][A-Z]',x)),None)

def probe(case,derived):
    prior=json.loads((BASE/case/'run.json').read_text(encoding='utf-8'))
    exe=Path(prior['executable']);assert sha(exe)==prior['executable_sha256']
    files={k:Path(v['path']) for k,v in prior['inputs'].items()}
    assert all(sha(p)==prior['inputs'][k]['sha256'] for k,p in files.items())
    original_bia=files['BIA'];files['BIA']=derived
    folder=OUT/case;folder.mkdir(exist_ok=False)
    output=folder/'solution.csv'
    env=environment(os.environ,files)
    env.update(RTK_PPP_OUTPUT=str(output),RTK_PPP_TRACE=str(folder/'solution.trace'),RTK_PPP_TRACE_LEVEL='2')
    command=[str(exe),'--source','txt-fast','--no-gui','--max-epochs','30']
    with (folder/'preflight.log').open('wb') as log:
        check=subprocess.run(command+['--check-files'],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
    assert check.returncode==0
    with (folder/'console.log').open('wb') as log:
        result=subprocess.run(command,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
    assert result.returncode==0
    with output.open() as a,(BASE/case/'solution.csv').open() as b:
        actual,expected=[list(csv.DictReader(f)) for f in (a,b)]
    expected=expected[:30]
    assert len(actual)==len(expected)==30
    differences=[(i+1,k) for i,(a,b) in enumerate(zip(actual,expected)) for k in a if k!='processing_ms' and a[k]!=b[k]]
    assert not differences,differences[:10]
    receipt=dict(executable=str(exe),executable_sha256=sha(exe),command=command,
        preflight_returncode=check.returncode,returncode=result.returncode,epochs=30,
        comparison='Exact field equality to original-BIA baseline prefix, excluding processing_ms',
        changed_fields=0,derived_BIA=str(derived),derived_BIA_sha256=sha(derived),
        original_BIA=str(original_bia),original_BIA_sha256=sha(original_bia),
        baseline_run=str(BASE/case/'run.json'),baseline_solution_sha256=sha(BASE/case/'solution.csv'))
    save(folder/'run.json',receipt)
    return receipt

def main():
    OUT.mkdir(exist_ok=False)
    prior=json.loads((BASE/'k70/run.json').read_text(encoding='utf-8'))
    bia=Path(prior['inputs']['BIA']['path']);assert sha(bia)==prior['inputs']['BIA']['sha256']
    lines=bia.read_bytes().splitlines(keepends=True)
    records=Counter();phase_signals=Counter();kept=[];removed=[]
    for line in lines:
        text=line.decode('ascii',errors='replace');code=obs_type(text)
        if code:records[code[0]]+=1
        if code and code[0]=='L':
            removed.append(line);phase_signals[text.split()[2][0]+'_'+code]+=1
        else:kept.append(line)
    assert records['C']==867 and records['L']==15007
    derived=OUT/'same_code_without_phase_osb.BIA';derived.write_bytes(b''.join(kept))
    assert [l for l in lines if (obs_type(l.decode('ascii',errors='replace')) or '').startswith('C')]==[
        l for l in kept if (obs_type(l.decode('ascii',errors='replace')) or '').startswith('C')]
    sources={str(ROOT/p):sha(ROOT/p) for p in ['src/preceph.c','src/ppp.c','src/gnss_replay.c','src/postpos.c','src/rtklib.h']}
    with ThreadPoolExecutor(max_workers=2) as pool:results=dict(zip(['k70','iq'],pool.map(lambda case:probe(case,derived),['k70','iq'])))
    assert sha(bia)==prior['inputs']['BIA']['sha256']
    assert all(sha(p)==digest for p,digest in sources.items())
    summary=dict(date='2026-11-08',scope='Oct31 B_VERIFIED fixed-clock TXT file-product path',
        original_BIA=str(bia),original_BIA_sha256=sha(bia),original_record_types=dict(records),
        phase_records_by_system_signal=dict(phase_signals),phase_rows_removed=len(removed),
        code_rows_byte_identical=True,probes=results,sources_unchanged=sources,
        conclusion='BIA phase OSBs are present in the input file but not read or applied by this TXT file-product path. Code OSBs are used. SSR phase-bias path is separate and inactive.',
        limit='30-epoch runtime probes plus source inspection; not a test enabling phase OSB and not a diagnosis of the metre-level error cause.')
    save(OUT/'summary.json',summary)
    (OUT/'REPORT.md').write_text('''# 10/31 TXT 解算相位 OSB 参与核查

结论：本次 K70/IQ 文件产品解算没有施加 BIA 相位 OSB；码 OSB 有参与。原 BIA 中有 867 条 C 类码 OSB、15007 条 L 类相位 OSB，文件存在相位记录不等于程序使用。

## 路径证据

- src/gnss_replay.c::load_products 调用 readdcb 读取 BIA，TXT 逐期直接进入 rtkpos。
- src/preceph.c::readbiaf 只识别以 C 开头的三字符观测名，L 记录没有 obs1，直接跳过；存储/查询为 codeosb_t/codeosb_at。
- src/ppp.c::corr_meas 的 L 改正为 L_raw*c/f − 卫星天线项 − 接收机天线项 − 相位缠绕项，没有 BIA 相位 OSB；P 分支调用 codeosb_at 并减去码 OSB。
- src/postpos.c::corr_phase_bias_ssr 使用 nav->ssr[].pbias，属于另一条 SSR 调度路径；本次 TXT 不经过该函数，日志明确 FILE_PRODUCTS_ONLY / SSR=OFF。不能把 BIA 相位 OSB 与 SSR pbias 混为一谈。

## 实际 EXE 验证

原 BIA 和所有生产文件不动，另存一份只移除 15007 条 L 记录的 BIA。867 条 C 记录按字节核对完全相同，其余元数据保持。使用本次实际 EXE（SHA b21c0420e7ebcf85251ede0dd4b06c20a05530cf4fe8560dd027f5d957826944）对 K70 和 IQ 各回放前 30 历元，预检均通过，结果除 processing_ms 外所有字段与原 BIA 基线逐字段相同。完整命令及 SHA 在各 run.json，统计在 summary.json。

## 解释边界

这确认当前路径未使用相位 OSB，不代表已经证明它是约 2 m 高程偏差的根因。本次没有启用相位 OSB、没有修改算法或产品原件，也未进行完整精度对照。历史 raPPPid 路径曾在 phase=off 字段下实际施加相位 OSB，不能把该字段或其行为套用到本项目。若后续验证相位 OSB，应另行核对精确轨钟参考、相位有效期和跳变、信号身份、模糊度初始化/连续性；不能只加一个相位减项便宣称修复。
''',encoding='utf-8')
    print(json.dumps(dict(record_types=dict(records),probes={k:dict(epochs=v['epochs'],changed_fields=v['changed_fields']) for k,v in results.items()},conclusion=summary['conclusion']),ensure_ascii=False,indent=2))

if __name__=='__main__':main()
