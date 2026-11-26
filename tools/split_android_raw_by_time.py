"""Lossless Android Raw segmentation by a fixed hardware-clock reference.

Copies original bytes, groups whole callbacks, never regenerates P/L/D or flags.
Output directory must not already exist. Verification concatenates all output
Raw rows and compares their count and SHA256 with the source measurement stream.
"""
from pathlib import Path
from decimal import Decimal, getcontext
import argparse, datetime as dt, hashlib, json

getcontext().prec = 50
NS = 10**9
GPS_EPOCH = dt.datetime(1980, 1, 6)

def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024), b''):h.update(block)
    return h.hexdigest()

def stamp(ns, leap=0, local=False):
    sec, rem = divmod(int(ns), NS)
    t = GPS_EPOCH + dt.timedelta(seconds=sec - (leap if local else 0) + (28800 if local else 0))
    return t.strftime('%Y-%m-%d %H:%M:%S') + f'.{rem:09d}' + (' +08:00' if local else ' GPST')

def split(source, output, minutes):
    source, output = source.resolve(), output.resolve()
    if minutes <= 0:raise ValueError('minutes must be positive')
    if output.exists():raise FileExistsError(f'Refuse to overwrite: {output}')
    output.mkdir(parents=True, exist_ok=False)
    width = Decimal(minutes*60*NS)
    header, payload, records = [], [], []
    key, start, previous_gps, previous_time, previous_hcdc = None,None,None,None,None
    ref, active, sink, segment = None,None,None,0
    clock_segments, parts = [],[]
    raw_hash = hashlib.sha256();source_raw_count = 0;source_epoch_count = 0
    previous_index = -1

    def flush():
        nonlocal start,previous_gps,previous_time,previous_hcdc,ref,active,sink,segment,previous_index,source_epoch_count
        if not records:return
        time, hcdc = key
        reset = previous_time is not None and (hcdc!=previous_hcdc or time<previous_time)
        if ref is None or reset:
            candidate = None
            for _, fields in records:
                try:
                    fb = int(fields[5]);bias=Decimal(fields[6].decode('ascii') or '0')
                    if not bias.is_finite():continue
                    candidate=(fb,bias);break
                except (ValueError,ArithmeticError):continue
            if candidate is None:raise ValueError('Cannot establish a valid clock reference')
            ref=candidate;segment+=1
            clock_segments.append({'segment':segment,'source_row':records[0][0],
                'hcdc':hcdc,'full_bias_ref':ref[0],'bias_ref_ns':str(ref[1]),
                'reason':'INITIAL' if previous_time is None else 'HARDWARE_DISCONTINUITY'})
        gps=Decimal(time-ref[0])-ref[1]
        if gps<0:raise ValueError('Negative GPST')
        if previous_gps is not None and gps<previous_gps:raise ValueError('GPST is not monotonic; no silent sorting')
        if start is None:start=gps
        index=int((gps-start)//width)
        if index<previous_index:raise ValueError('Backward segment index')
        if index!=previous_index:
            if sink:sink.close()
            filename=f'{source.stem}_part{index+1:02d}_{index*minutes:02d}-{(index+1)*minutes:02d}min.txt'
            path=output/filename;sink=path.open('xb')
            for line in header:sink.write(line)
            active={'file':filename,'part':index+1,'nominal_offset_seconds':[index*minutes*60,(index+1)*minutes*60],
                'epochs':0,'raw_rows':0,'source_first_row':records[0][0],'source_last_row':records[-1][0],
                'first_gps_ns':str(gps),'last_gps_ns':str(gps),'first_hardware_time_ns':time,
                'last_hardware_time_ns':time,'clock_segments':[],'time_offset_min_ns':None,'time_offset_max_ns':None}
            parts.append(active);previous_index=index
        for line in payload:sink.write(line)
        leap=int(records[0][1][3]) if records[0][1][3] else 18
        if not 0<=leap<=100:raise ValueError('Invalid leap second metadata')
        active['epochs']+=1;active['raw_rows']+=len(records);source_epoch_count+=1
        active['source_last_row']=records[-1][0];active['last_gps_ns']=str(gps);active['last_hardware_time_ns']=time
        active.setdefault('leap_seconds',leap)
        if segment not in active['clock_segments']:active['clock_segments'].append(segment)
        for _,f in records:
            offset=Decimal(f[12].decode('ascii') or '0')
            if not offset.is_finite():raise ValueError('Invalid TimeOffsetNanos')
            lo=active['time_offset_min_ns'];hi=active['time_offset_max_ns']
            active['time_offset_min_ns']=str(offset if lo is None else min(Decimal(lo),offset))
            active['time_offset_max_ns']=str(offset if hi is None else max(Decimal(hi),offset))
        previous_gps,previous_time,previous_hcdc=gps,time,hcdc

    try:
        with source.open('rb') as f:
            for number,line in enumerate(f,1):
                if not line.startswith(b'Raw,'):
                    if key is None:header.append(line)
                    else:payload.append(line)
                    continue
                fields=line.rstrip(b'\r\n').split(b',')
                if len(fields)<37:raise ValueError(f'Truncated Raw row {number}')
                newkey=(int(fields[2]),int(fields[10]))
                if key is not None and newkey!=key:
                    flush();payload=[];records=[]
                key=newkey;payload.append(line);records.append((number,fields))
                source_raw_count+=1;raw_hash.update(line)
        flush()
    finally:
        if sink:sink.close()
    if not parts:raise ValueError('No Raw observations')
    combined=hashlib.sha256();rows=0;last_key=None
    for p in parts:
        path=output/p['file'];p['sha256']=digest(path);p['bytes']=path.stat().st_size
        keys=[]
        with path.open('rb') as f:
            for line in f:
                if not line.startswith(b'Raw,'):continue
                combined.update(line);rows+=1
                c=line.split(b',');k=(int(c[2]),int(c[10]))
                if not keys or keys[-1]!=k:keys.append(k)
        if len(keys)!=p['epochs']:raise AssertionError('Epoch count mismatch')
        if last_key==keys[0]:raise AssertionError('A callback was split across files')
        last_key=keys[-1]
        for bound in ['first','last']:
            value=Decimal(p[f'{bound}_gps_ns'])
            p[f'{bound}_gps_time']=stamp(value)
            p[f'{bound}_beijing_time']=stamp(value,p['leap_seconds'],True)
        p['sample_span_seconds']=float((Decimal(p['last_gps_ns'])-Decimal(p['first_gps_ns']))/NS)
    assert rows==source_raw_count and combined.digest()==raw_hash.digest()
    result={'source':str(source),'source_sha256':digest(source),'minutes':minutes,
        'boundary':'Half-open intervals [t0+600*i,t0+600*(i+1)); whole callbacks, not byte count',
        'source_raw_rows':source_raw_count,'source_epochs':source_epoch_count,
        'source_span_seconds':float((previous_gps-start)/NS),'raw_payload_sha256':raw_hash.hexdigest(),
        'verification':{'same_raw_count':True,'concatenated_raw_bytes_sha256_identical':True,'no_callback_split':True},
        'clock_segments':clock_segments,'parts':parts,
        'notes':['Source and phone files retained unchanged. No P/L/D, HCDC or ADR flags regenerated.',
          'Each part has the original file header. Source footer comments occur only in their original final part.',
          'Independent PPP runs reinitialize states; file boundaries are not new hardware clock events.',
          'Clock references are preserved in this manifest. Standalone converters otherwise initialize from their part first sample.']}
    (output/'split_manifest.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    lines=['# 10分钟原始观测分段','',f'源文件：`{source}`',
        f'实际首末样本跨度：{result["source_span_seconds"]:.3f} 秒；{source_epoch_count} 个回调，{source_raw_count} 条Raw。',
        '', '|文件|北京时间首样本|北京时间末样本|回调数|Raw行数|','|---|---|---|---:|---:|']
    for p in parts:lines.append(f'|{p["file"]}|{p["first_beijing_time"]}|{p["last_beijing_time"]}|{p["epochs"]}|{p["raw_rows"]}|')
    lines+=['','按首个有效GNSS观测时刻起每600秒划分，尾段不足10分钟仍保留；没有补造数据或改写原始字段。',
        '全部分段Raw行按顺序连接后，数量及SHA256与原始Raw数据流一致；同一回调没有跨文件。',
        '分段不等于硬件钟跳变，也不添加周跳标志。每段单独启动PPP会重新初始化，不能直接等同于一小时连续滤波结果。',
        '只有文件切分，没有执行PPP解算、改变参数或生成平滑/修复观测。']
    (output/'README.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'parts':len(parts),'epochs':source_epoch_count,'raw_rows':rows,
        'span_seconds':result['source_span_seconds'],'verified':True,'output':str(output)},ensure_ascii=False))

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('source',type=Path)
    ap.add_argument('--output-dir',required=True,type=Path);ap.add_argument('--minutes',type=int,default=10)
    a=ap.parse_args();split(a.source,a.output_dir,a.minutes)
