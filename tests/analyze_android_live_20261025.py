"""Read-only comparison of the real Oct25 phone capture and controlled PC replays.

Uses the user-confirmed current reference. Never feeds reference coordinates or
diagnostic measurements back into the solver. Large original phone files stay intact.
"""
import csv
import gzip
import json
import math
from collections import Counter
from pathlib import Path

from four_sample_diagnosis import np, P

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'validation/android_live_20261025_v1'
LIVE = 'ppp_b_verified_1792906436690'


def save(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding='utf-8')


def csvwrite(name, rows):
    with (OUT / name).open('w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def csvread(path):
    stream = path.open(encoding='utf-8-sig') if path.exists() else gzip.open(str(path)+'.gz','rt',encoding='utf-8-sig')
    with stream as f:
        return list(csv.DictReader(f))


def key(tow):
    return round(float(tow) * 1e6)


def load_solution(path):
    if path.suffix == '.csv':
        return {key(x['tow']): dict(q=int(x['Q']), ns=int(x['ns']),
            xyz=np.array([float(x[k]) for k in ['x_m', 'y_m', 'z_m']]),
            ms=float(x['processing_ms'])) for x in csvread(path)}
    out = {}
    for line in path.read_text().splitlines():
        if not line.strip() or line.startswith('%'):
            continue
        x = line.split()
        if len(x) < 15:  # preserve but do not treat the killed phone's last partial row as complete
            continue
        hh, mm, ss = map(float, x[1].split(':'))
        out[key(hh*3600+mm*60+ss)] = dict(q=int(x[5]), ns=int(x[6]),
            xyz=np.array(P.ecef(*map(float, x[2:5]))))
    return out


def observations(path):
    return {(key(x['tow']), x['sat'], x['signal']): x for x in csvread(path)}


def rinex_observations(path):
    types, result = {}, {}
    tow = None
    with path.open() as f:
        for line in f:
            if 'SYS / # / OBS TYPES' in line:
                types[line[0]] = line[7:60].split()
            elif line.startswith('>'):
                x = line[1:].split()
                tow = key(int(x[3])*3600 + int(x[4])*60 + float(x[5]))
            elif tow is not None and line[:1] in types and line[1:3].isdigit():
                for i, typ in enumerate(types[line[0]]):
                    field = line[3+i*16:3+(i+1)*16]
                    if not field[:14].strip():
                        continue
                    row = result.setdefault((tow, line[:3], typ[1:]), {})
                    row[typ[0]] = float(field[:14])
                    if typ[0] == 'L':
                        row['LLI'] = int(field[14:15].strip() or 0)
    return result


def compare_observations(live, other):
    common = live.keys() & other.keys()
    maxima = {k: max(abs(float(live[i][k])-float(other[i][k])) for i in common)
        for k in ['P_m', 'L_cycle', 'D_Hz', 'CN0_dBHz']}
    return dict(live_rows=len(live), other_rows=len(other), common_rows=len(common),
        missing_live_identity=len(live.keys()-other.keys()), max_value_difference=maxima,
        LLI_differences=sum(live[i]['LLI'] != other[i]['LLI'] for i in common),
        code_differences=sum(live[i]['code'] != other[i]['code'] for i in common),
        slot_differences=sum(live[i]['slot'] != other[i]['slot'] for i in common))


def continuous_start(times, good, seconds=60):
    start = None
    for t, ok, dt in zip(times, good, np.r_[0, np.diff(times)]):
        if not ok or dt > 1.01:
            start = None
        if ok:
            if start is None:
                start = t
            if t-start >= seconds:
                return float(start)
    return None


def raw_phase_reasons(live, rinex, pc_all):
    """Trace missing offline L to raw ADR gating without guessing signal identity."""
    reasons, rows = Counter(), []
    full_times = list(pc_all)
    index, previous = -1, None
    sysmap = {1: 'G', 5: 'C', 6: 'E'}
    bands = {'G': [(1575420000, '1'), (1176450000, '5')],
             'E': [(1575420000, '1'), (1176450000, '5'), (1207140000, '7')],
             'C': [(1575420000, '1'), (1561098000, '2'), (1176450000, '5')]}
    for line in (OUT / 'inputs/RawData_20261025_133353.txt').open():
        if not line.startswith('Raw,'):
            continue
        a = line.rstrip('\n').split(',')
        if a[2] != previous:
            previous = a[2]
            index += 1
        system = sysmap.get(int(a[28]))
        if not system:
            continue
        freq = float(a[22] or 0)
        band = next((b for f, b in bands[system] if abs(freq-f) < 10000), None)
        if not band or not a[35]:
            continue
        signal = band + a[35]
        ident = (full_times[index], f'{system}{int(a[11]):02d}', signal)
        x, y = live.get(ident), rinex.get(ident)
        if x is None or y is None or not float(x['L_cycle']) or y.get('L', 0):
            continue
        state, unc = int(a[19]), float(a[21])
        if state & 6:
            reason = 'OFFLINE_DROPS_ADR_RESET_OR_SLIP_LIVE_FORWARDS_L_WITH_ARC_EVIDENCE'
        elif unc > .5:
            reason = 'ADR_UNCERTAINTY_0P5_TO_1P0_M_DIFFERENT_GATE'
        else:
            reason = 'OTHER_OFFLINE_PATH_DIFFERENCE'
        reasons[reason] += 1
        rows.append(dict(tow=ident[0]/1e6, sat=ident[1], signal=signal,
            ADR_state=state, ADR_uncertainty_m=unc, live_L_cycle=x['L_cycle'],
            live_LLI=x['LLI'], reason=reason))
    assert index+1 == len(full_times)
    csvwrite('offline_missing_phase_evidence.csv', rows)
    return dict(reasons)


def main():
    ref = json.loads((OUT / 'reference.json').read_text())
    lat, lon, height = ref['latitude_deg'], ref['longitude_deg'], ref['ellipsoidal_height_m']
    origin = np.array(P.ecef(lat, lon, height))
    la, lo = math.radians(lat), math.radians(lon)
    rot = np.array([[-math.sin(lo), math.cos(lo), 0],
        [-math.sin(la)*math.cos(lo), -math.sin(la)*math.sin(lo), math.cos(la)],
        [math.cos(la)*math.cos(lo), math.cos(la)*math.sin(lo), math.sin(la)]])
    paths = {'PHONE_LIVE': OUT/'live'/f'{LIVE}.solution.csv',
        'PC_RAW_ALL': OUT/'pc_txt-fast/solution.csv',
        'PC_RINEX_ALL': OUT/'pc_rinex/solution.pos',
        'PC_RAW_LIVE_WINDOW': OUT/'pc_live_window/solution.csv',
        'PHONE_POST_PARTIAL': OUT/'post/PPP_Result_1792908017112.pos'}
    if (OUT/'pc_raw_matching_atx/solution.csv.session.json').exists():
        receipt = json.loads((OUT/'pc_raw_matching_atx/solution.csv.session.json').read_text())
        if receipt.get('status') == 'COMPLETE':
            paths['PC_RAW_MATCHING_ATX'] = OUT/'pc_raw_matching_atx/solution.csv'
    cases = {name: load_solution(p) for name, p in paths.items()}
    live = cases['PHONE_LIVE']
    first, last = min(live), max(live)
    rows, metrics, curves = [], {}, {}
    for name, case in cases.items():
        keys = sorted(k for k in case if first <= k <= last)
        t = np.array([(k-first)/1e6 for k in keys])
        enu = np.array([(case[k]['xyz']-origin) @ rot.T for k in keys])
        q = np.array([case[k]['q'] for k in keys])
        H = np.linalg.norm(enu[:, :2], axis=1)
        m = dict(epochs_total=len(case), common_window_rows=len(keys),
            Q=dict(Counter(map(int, q))), last_ENU_m=enu[-1].tolist(),
            last_H_m=float(H[-1]), last_3D_m=float(np.linalg.norm(enu[-1])),
            max_H_m=float(H.max()), first_60s_continuous_H_below_1m=continuous_start(t, (q==6)&(H<1)))
        for lo_sec, hi_sec in [(0,60),(60,300),(300,900),(900,1600),(60,1600)]:
            select = (q==6)&(t>=lo_sec)&(t<hi_sec)
            if select.any():
                m[f'window_{lo_sec}_{hi_sec}'] = dict(N=int(select.sum()),
                    mean_ENU_m=enu[select].mean(axis=0).tolist(),
                    H_RMS_m=float(np.sqrt(np.mean(H[select]**2))),
                    U_RMS_m=float(np.sqrt(np.mean(enu[select,2]**2))))
        ms = [x['ms'] for x in case.values() if 'ms' in x]
        if ms:
            m['processing_ms'] = dict(median=float(np.median(ms)), p95=float(np.percentile(ms,95)), max=max(ms))
        if name != 'PHONE_LIVE':
            diff = np.array([(case[k]['xyz']-live[k]['xyz']) @ rot.T for k in keys])
            m['vs_live'] = dict(common=len(keys), max_abs_ENU_m=np.abs(diff).max(axis=0).tolist(),
                last_ENU_m=diff[-1].tolist(), Q_differences=sum(case[k]['q']!=live[k]['q'] for k in keys))
        metrics[name] = m
        curves[name] = (t, enu, H)
        for j, k in enumerate(keys):
            rows.append(dict(case=name,tow=k/1e6,elapsed_s=t[j],Q=int(q[j]),ns=case[k]['ns'],
                E_m=enu[j,0],N_m=enu[j,1],U_m=enu[j,2],H_m=H[j],error_3D_m=np.linalg.norm(enu[j])))
    # Exact same input and starting epoch is the decisive realtime/PC control.
    paired = cases['PC_RAW_LIVE_WINDOW']
    assert set(paired) == set(live)
    assert all(paired[k]['q'] == live[k]['q'] and paired[k]['ns'] == live[k]['ns'] for k in live)
    max_xyz = np.max(np.abs(np.array([paired[k]['xyz']-live[k]['xyz'] for k in live])),axis=0)
    metrics['same_window_control_max_abs_XYZ_m'] = max_xyz.tolist()
    assert max_xyz.max() < 1e-3, max_xyz
    # Check independent ENU recomputation against the app's persisted error CSV.
    error_rows = csvread(OUT/'live'/f'{LIVE}.errors.csv')
    errors = np.array([[float(x[k]) for k in ['E_m','N_m','U_m']] for x in error_rows])
    metrics['app_ENU_reconstruction_max_difference_m'] = float(np.max(np.abs(errors-curves['PHONE_LIVE'][1])))
    assert metrics['app_ENU_reconstruction_max_difference_m'] < 1e-7
    # The previously interrupted Android postprocessing must match the PC rerun prefix.
    a,b = cases['PHONE_POST_PARTIAL'],cases['PC_RINEX_ALL']
    keys = sorted(a.keys() & b.keys())
    diff = np.array([a[k]['xyz']-b[k]['xyz'] for k in keys])
    metrics['phone_post_prefix_vs_PC'] = dict(rows=len(keys),max_abs_XYZ_m=np.abs(diff).max(axis=0).tolist(),
        Q_differences=sum(a[k]['q']!=b[k]['q'] for k in keys))
    assert np.max(np.abs(diff)) < 1e-3
    if 'PC_RAW_MATCHING_ATX' in cases:
        control = json.loads((OUT/'pc_txt-fast/manifest.json').read_text())
        trial = json.loads((OUT/'pc_raw_matching_atx/manifest.json').read_text())
        assert control['source'] == trial['source']
        assert [k for k in control['files'] if control['files'][k] != trial['files'][k]] == ['ATX']
        a, b = cases['PC_RAW_ALL'], cases['PC_RAW_MATCHING_ATX']
        assert a.keys() == b.keys()
        keys = sorted(a)
        delta = np.array([(b[k]['xyz']-a[k]['xyz']) @ rot.T for k in keys])
        metrics['ATX_only_same_raw_all_control'] = dict(epochs=len(keys),
            max_abs_ENU_change_m=np.abs(delta).max(axis=0).tolist(),
            final_ENU_change_m=delta[-1].tolist(),
            Q_differences=sum(a[k]['q'] != b[k]['q'] for k in keys))
    csvwrite('coordinate_time_series.csv', rows)

    live_obs = observations(OUT/'live'/f'{LIVE}.obs.csv')
    raw_obs = observations(OUT/'pc_live_window/solution.csv.obs.csv')
    control = compare_observations(live_obs, raw_obs)
    assert control['missing_live_identity'] == control['LLI_differences'] == control['code_differences'] == control['slot_differences'] == 0
    assert all(v==0 for v in control['max_value_difference'].values())
    save('same_window_input_control.json', control)
    rinex = rinex_observations(OUT/'inputs/GEOL00CHN_R_20262980533_00U_01S_MO.rnx')
    metrics['missing_offline_phase_raw_reasons'] = raw_phase_reasons(live_obs,rinex,cases['PC_RAW_ALL'])
    save('metrics.json',metrics)

    import matplotlib.pyplot as plt
    plt.rcParams['font.family'] = 'DejaVu Sans'
    fig, axes = plt.subplots(3,1,figsize=(11,9),sharex=True)
    for name in ['PHONE_LIVE','PC_RINEX_ALL','PC_RAW_LIVE_WINDOW','PC_RAW_MATCHING_ATX']:
        if name not in curves:
            continue
        t, enu, H = curves[name]
        style = {'PHONE_LIVE':dict(color='#1769aa',lw=1.5),
                 'PC_RINEX_ALL':dict(color='#d2691e',lw=1.2),
                 'PC_RAW_LIVE_WINDOW':dict(color='#249966',lw=1,ls='--'),
                 'PC_RAW_MATCHING_ATX':dict(color='#8c4aa4',lw=1,ls=':')}[name]
        for ax, values in zip(axes,[H,enu[:,2],enu[:,0]]):
            ax.plot(t,values,label=name,**style)
    for ax,label in zip(axes,['Horizontal error (m)','Up error (m)','East error (m)']):
        ax.set_ylabel(label);ax.grid(alpha=.25)
    axes[0].axhline(1,color='gray',ls=':',label='1 m (diagnostic only)')
    axes[0].legend(fontsize=8,loc='upper right')
    axes[1].axhline(0,color='gray',lw=.7);axes[2].axhline(0,color='gray',lw=.7)
    axes[-1].set_xlabel('Seconds since live start (GPST 2026-10-25 05:34:14.001)')
    fig.suptitle('Oct25 phone live vs same-file replay | user-confirmed ellipsoidal reference')
    fig.tight_layout();fig.savefig(ROOT/'docs/ANDROID_LIVE_POST_COMPARISON_20261025.png',dpi=160);plt.close(fig)
    print(json.dumps({k:v for k,v in metrics.items() if k not in ['PHONE_POST_PARTIAL']},indent=2))


if __name__ == '__main__':
    main()
