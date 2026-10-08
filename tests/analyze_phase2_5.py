"""Phase 2.5 offline innovation audit. This module never imports estimator code.

Only CSV observations are read; all classifications are descriptive output. The
strict future Phase-D pool is GNSS_CODE and excludes ANY current-observation
initialization, including states outside that row's H support. A separate
structural pool exposes how many rows survive lifecycle screening. It is not a
learning pool. Persistent-bias flags mean a complete 10/30/60-row window has one
nonzero sign; this is transparent candidate evidence, not a final bias rule.

Temporal statistics use STABLE NORMAL_CONTINUOUS FIRST_PREFIT rows. Tracks are
split at innovation absence, timestamp/epoch discontinuity, signal/arc change,
slip, reset/initialization, reject or edited reentry. States
initialized from current data remain visible to this diagnostic (and therefore
can explain correlations), but are never eligible learning candidates.

Autocorrelation uses each segment's own mean, then pools cross-products and
norms across segments without creating cross-segment pairs. ESS uses dense
lags 1..min(30,N-1), positive lag-pair truncation and a finite-length
factor. It is a capped, finite-lag descriptive approximation; summed arc ESS
does not establish independence between satellites, signals or arcs.
"""
from pathlib import Path
import argparse
import collections
import csv
import hashlib
import json
import math
import statistics

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / 'validation' / 'phase2_5'
LAGS = (1, 2, 5, 10, 30)
WINDOWS = (10, 30, 60)
INIT_TAGS = {'ARC_INIT', 'ARC_RESTART', 'ARC_RECOVERY'}
REQUIRED = {'baseline', 'sys', 'signal', 'sat', 'obs_type', 'measurement_class',
    'stage', 'epoch', 'row', 'trial', 'elapsed_s', 'sample_scope', 'v', 'u',
    'obs_var', 'pred_var', 'Sii', 'finite_flag', 'legacy_reject_flag', 'slip_flag',
    'combined', 'frequency_slot', 'lifecycle_tags', 'state_init_from_current_obs',
    'state_init_affects_row', 'ambiguity_init_from_current_obs', 'same_epoch_reentry',
    'arc_id', 'arc_age', 'continuous_epochs', 'gap_flag', 'signal_switch_flag',
    'provenance_valid','posterior_committed','epoch_failure','inactive_state_support',
    'arc_status','cn0_dbhz','elevation_deg','clock_m','clock_var','isb_m','isb_var',
    'iono_m','iono_var','trop_m','trop_var','ambiguity_m','spp_attempted','spp_from_current_obs'}


def number(row, name, default=math.nan):
    try:
        return float(row.get(name, default))
    except (ValueError, TypeError):
        return default


def flag(row, name):
    return number(row, name, 0) != 0


def stage(row):
    return 'STABLE' if row['stage'] in ('STEADY', 'STABLE') else row['stage']


def tags(row):
    return set(filter(None, row.get('lifecycle_tags', '').split('|')))


def first(row):
    return row['sample_scope'] == 'FIRST_PREFIT' and number(row, 'trial') == 0


def valid(row):
    return row['finite_flag'] == '1' and all(math.isfinite(number(row, k))
        for k in ('v', 'u', 'obs_var', 'pred_var', 'Sii')) and number(row, 'Sii') > 0


def group_key(row):
    return (row['baseline'], row['sys'], row['signal'], row['obs_type'], stage(row))


def group_dict(key):
    return dict(zip(('baseline', 'sys', 'signal', 'obs_type', 'stage'), key))


def describe(rows):
    """Sample std and population centered variance are intentionally distinct."""
    n = len(rows)
    values = {k: [number(r, k) for r in rows] for k in ('v', 'u', 'pred_var', 'obs_var')}
    result = {'N': n}
    for name in ('v', 'u'):
        a = values[name]
        mean = statistics.fmean(a) if n else None
        result.update({f'mean_{name}': mean,
            f'median_{name}': statistics.median(a) if n else None,
            f'std_{name}': statistics.stdev(a) if n > 1 else None})
    if not n:
        return result
    v = values['v']; mean = result['mean_v']
    m2 = statistics.fmean(x*x for x in v)
    centered = statistics.fmean((x-mean)**2 for x in v)
    pred = statistics.fmean(values['pred_var'])
    result.update(RMS_v=math.sqrt(m2), positive_ratio=sum(x > 0 for x in v)/n,
        negative_ratio=sum(x < 0 for x in v)/n, zero_ratio=sum(x == 0 for x in v)/n,
        mean_v_squared=m2, variance_around_sample_mean_population=centered,
        mean_pred_var=pred, mean_Rii=statistics.fmean(values['obs_var']),
        candidate_noise_raw_second_moment=m2-pred,
        candidate_noise_centered_variance=centered-pred,
        mean_squared_inflation=m2-centered,
        mean_squared_identity_error=(m2-centered)-mean*mean,
        squared_mean_fraction_of_second_moment=mean*mean/m2 if m2 > 0 else None,
        mean_v_over_std_v=mean/result['std_v'] if result['std_v'] else None)
    return result


def eligibility(row, persistent_candidate=False):
    """Multi-label exclusion; no result feeds back to the estimator."""
    reasons = []
    details = []
    life = tags(row)
    if stage(row) == 'STARTUP': reasons.append('INELIGIBLE_STARTUP')
    # ARC_PENDING_INIT is not automatically an initialization event for code.
    if life & INIT_TAGS or flag(row, 'ambiguity_init_from_current_obs'):
        reasons.append('INELIGIBLE_ARC_INIT')
    if flag(row, 'slip_flag'): reasons.append('INELIGIBLE_SLIP')
    if flag(row, 'gap_flag') or 'POST_GAP' in life:
        reasons.append('INELIGIBLE_GAP')
    if flag(row, 'legacy_reject_flag'): reasons.append('INELIGIBLE_REJECT')
    if not first(row) or flag(row, 'same_epoch_reentry') or 'EDIT_RETRY' in life:
        reasons.append('INELIGIBLE_RETRY')
    if any(flag(row, k) for k in ('state_init_from_current_obs',
            'ambiguity_init_from_current_obs', 'legacy_current_obs_adjustment')):
        reasons.append('INELIGIBLE_CURRENT_OBS_INIT')
    if persistent_candidate: reasons.append('INELIGIBLE_PERSISTENT_BIAS')
    if row['measurement_class'] not in ('GNSS_CODE', 'GNSS_PHASE'):
        reasons.append('INELIGIBLE_CONSTRAINT')
    if flag(row, 'combined'): reasons.append('INELIGIBLE_IFLC')
    if not valid(row): details.append('INVALID_INNOVATION')
    if not flag(row, 'provenance_valid'): details.append('UNKNOWN_INITIALIZATION_PROVENANCE')
    if flag(row, 'inactive_state_support'): details.append('INACTIVE_STATE_SUPPORT')
    if flag(row, 'epoch_failure') or not flag(row, 'posterior_committed'):
        details.append('EPOCH_NOT_COMMITTED')
    if flag(row, 'signal_switch_flag'): details.append('SIGNAL_SWITCH')
    if not row['signal'] and row['measurement_class'] in ('GNSS_CODE', 'GNSS_PHASE'):
        details.append('UNKNOWN_SIGNAL')
    if row['measurement_class'] == 'GNSS_PHASE': details.append('PHASE_NOT_FIRST_PHASE_D_POOL')
    if row['baseline'] == 'B' and row['measurement_class'] in ('GNSS_CODE','GNSS_PHASE'):
        # B's existing history, smoothing and penalties are an audit baseline;
        # its effective R is not the fixed R0 needed by a future noise learner.
        details.append('LEGACY_B_RANDOM_MODEL_AND_HISTORY_NOT_FIXED_R0')
        R0=number(row,'R0')
        if math.isfinite(R0) and not math.isclose(number(row,'obs_var'),R0,rel_tol=1e-12,abs_tol=1e-12):
            details.append('LEGACY_EFFECTIVE_R_DIFFERS_FROM_R0')
    if details: reasons.append('INELIGIBLE_OTHER')
    structural_reasons = [r for r in reasons
        if r not in ('INELIGIBLE_CURRENT_OBS_INIT', 'INELIGIBLE_PERSISTENT_BIAS', 'INELIGIBLE_OTHER')]
    structural_details = [d for d in details if d not in ('PHASE_NOT_FIRST_PHASE_D_POOL',
        'LEGACY_B_RANDOM_MODEL_AND_HISTORY_NOT_FIXED_R0','LEGACY_EFFECTIVE_R_DIFFERS_FROM_R0')]
    structural = not structural_reasons and not structural_details
    return reasons, details, structural


def temporal_ok(row):
    """Current-data initialization is deliberately observed, not learned."""
    life = tags(row)
    return (first(row) and valid(row) and stage(row) == 'STABLE'
        and 'NORMAL_CONTINUOUS' in life and not life & INIT_TAGS
        and not any(flag(row, k) for k in ('slip_flag', 'gap_flag',
            'signal_switch_flag', 'legacy_reject_flag', 'same_epoch_reentry',
            'ambiguity_init_from_current_obs', 'inactive_state_support', 'epoch_failure'))
        and flag(row, 'posterior_committed')
        and not flag(row, 'combined'))


def cadence(rows):
    per_dataset = collections.defaultdict(dict)
    for r in rows:
        if first(r): per_dataset[r['dataset']][int(number(r, 'epoch'))] = number(r, 'elapsed_s')
    result = {}
    for dataset, values in per_dataset.items():
        ordered = sorted(values.items())
        dt = [b[1]-a[1] for a, b in zip(ordered, ordered[1:])
            if b[0]-a[0] == 1 and b[1] > a[1]]
        result[dataset] = statistics.median(dt) if dt else 1.0
    return result


def build_segments(rows):
    """Slot-level tracks make A -> B -> A signal switches break both A arcs."""
    tracks = collections.defaultdict(list)
    for r in rows:
        if first(r) and r['measurement_class'] in ('GNSS_CODE', 'GNSS_PHASE'):
            key = (r['dataset'], r['baseline'], r['sys'], r['sat'],
                r['frequency_slot'], r['obs_type'])
            tracks[key].append(r)
    expected = cadence(rows)
    segments = []
    for key, track in sorted(tracks.items()):
        current = []
        for r in sorted(track, key=lambda q: (number(q, 'epoch'), number(q, 'row'))):
            good = temporal_ok(r)
            if current and good:
                p = current[-1]
                dt = number(r, 'elapsed_s')-number(p, 'elapsed_s')
                good_link = (number(r, 'epoch') == number(p, 'epoch')+1
                    and r['signal'] == p['signal'] and r.get('signal2', '') == p.get('signal2', '')
                    and r['arc_id'] == p['arc_id']
                    and abs(dt-expected[r['dataset']]) <= max(1e-6, expected[r['dataset']]*.01))
                if not good_link:
                    segments.append(current); current = []
            if not good:
                if current: segments.append(current)
                current = []
                continue
            current.append(r)
        if current: segments.append(current)
    for i, segment in enumerate(segments, 1):
        ident = f'SEG{i:05d}'
        for r in segment:
            r['continuous_analysis_segment'] = ident
            r['continuous_analysis_length'] = len(segment)
    return segments, expected


def lag_terms(values, lag):
    """Center each complete arc; do not pool means across satellites/arcs."""
    if len(values) <= lag: return (0.0, 0.0, 0.0, 0)
    m = statistics.fmean(values)
    a = [x-m for x in values[:-lag]]
    b = [x-m for x in values[lag:]]
    return (sum(x*y for x,y in zip(a,b)), sum(x*x for x in a),
        sum(y*y for y in b), len(a))


def rho(terms):
    cross, a2, b2, n = terms
    return max(-1.0, min(1.0, cross/math.sqrt(a2*b2))) if n and a2 > 0 and b2 > 0 else None


def effective_sample_size(values, max_lag=30):
    n = len(values)
    if n < 3 or not statistics.pvariance(values):
        return None, None, 0
    max_lag = min(max_lag, n-1)
    rs = [rho(lag_terms(values, k)) for k in range(1, max_lag+1)]
    integral = 0.0
    used = 0
    # Positive pair truncation limits negative/unstable tail effects. A lone
    # last lag is included if positive; no infinite-lag extrapolation is made.
    for start in range(0, len(rs), 2):
        pair = rs[start:start+2]
        if any(x is None for x in pair): break
        weighted = sum((1-(start+i+1)/n)*x for i,x in enumerate(pair))
        if weighted <= 0: break
        integral += weighted; used += len(pair)
    tau = max(1.0, 1.0+2.0*integral)
    return max(1.0, min(float(n), n/tau)), tau, used


def paired_corr(a, b):
    pairs = [(x,y) for x,y in zip(a,b) if math.isfinite(x) and math.isfinite(y)]
    if len(pairs) < 3: return None
    x,y = zip(*pairs); mx,my = statistics.fmean(x),statistics.fmean(y)
    xx = sum((q-mx)**2 for q in x); yy = sum((q-my)**2 for q in y)
    return sum((q-mx)*(r-my) for q,r in pairs)/math.sqrt(xx*yy) if xx > 0 and yy > 0 else None


def segment_evidence(segment):
    v = [number(r,'v') for r in segment]; u = [number(r,'u') for r in segment]
    n = len(segment); info = describe(segment)
    first_row = segment[0]
    for k in ('dataset','baseline','sys','signal','obs_type','sat','frequency_slot','arc_id'):
        info[k] = first_row[k]
    info.update(segment_id=first_row['continuous_analysis_segment'], stage='STABLE',
        time_start=first_row.get('time',''), time_end=segment[-1].get('time',''),
        epoch_start=int(number(first_row,'epoch')), epoch_end=int(number(segment[-1],'epoch')),
        elapsed_start=number(first_row,'elapsed_s'), elapsed_end=number(segment[-1],'elapsed_s'),
        state_init_from_current_obs_count=sum(flag(r,'state_init_from_current_obs') for r in segment),
        state_init_affects_row_count=sum(flag(r,'state_init_affects_row') for r in segment),
        provenance_unknown_count=sum(not flag(r,'provenance_valid') for r in segment),
        spp_failed_attempt_count=sum(flag(r,'spp_attempted') and not flag(r,'spp_from_current_obs') for r in segment))
    for name,values in (('v',v),('u',u)):
        for lag in LAGS: info[f'rho_{name}_{lag}'] = rho(lag_terms(values,lag))
        ess,tau,used = effective_sample_size(values)
        info[f'effective_sample_size_{name}'] = ess
        info[f'integrated_time_{name}'] = tau
        info[f'ess_lags_used_{name}'] = used
    time = [number(r,'elapsed_s') for r in segment]
    mean_t = statistics.fmean(time); denom = sum((t-mean_t)**2 for t in time)
    info['linear_drift_v_m_per_s'] = sum((t-mean_t)*(x-info['mean_v']) for t,x in zip(time,v))/denom if denom else None
    info['drift_over_std_v'] = info['linear_drift_v_m_per_s']*(time[-1]-time[0])/info['std_v'] if denom and info['std_v'] else None
    info['max_same_sign_streak'] = same_sign_streaks(v)[1]
    for name in ('cn0_dbhz','elevation_deg','obs_var','pred_var','clock_m','iono_m','trop_m'):
        info[f'corr_v_{name}'] = paired_corr(v,[number(r,name) for r in segment])
        info[f'corr_u_{name}'] = paired_corr(u,[number(r,name) for r in segment])
    pred = [number(r,'pred_var') for r in segment]
    R = [number(r,'obs_var') for r in segment]
    total = [number(r,'Sii') for r in segment]
    info['mean_prediction_share'] = statistics.fmean(p/s for p,s in zip(pred,total))
    info['mean_measurement_share'] = statistics.fmean(r/s for r,s in zip(R,total))
    info['Rii_min'] = min(R); info['Rii_max'] = max(R)
    info['pred_var_min'] = min(pred); info['pred_var_max'] = max(pred)
    half = n//2
    info['variance_v_first_half'] = statistics.pvariance(v[:half]) if half else None
    info['variance_v_second_half'] = statistics.pvariance(v[half:]) if half else None
    info['evidence_note'] = 'Association only; current-observation initialization may induce shared structure; no causal attribution.'
    return info


def same_sign_streaks(values):
    streaks=[]; previous=0; length=0; longest=0
    for value in values:
        sign = (value>0)-(value<0)
        length = length+1 if sign and sign==previous else (1 if sign else 0)
        previous=sign; longest=max(longest,length); streaks.append(length)
    return streaks,longest


def rolling_evidence(segments):
    rows=[]
    for segment in segments:
        values=[number(r,'v') for r in segment]
        streaks,_=same_sign_streaks(values)
        for i,r in enumerate(segment):
            r['consecutive_same_sign_count']=streaks[i]
            flags=[]
            for window in WINDOWS:
                if i+1<window: continue
                selected=segment[i+1-window:i+1]; v=values[i+1-window:i+1]
                positive=sum(x>0 for x in v);negative=sum(x<0 for x in v)
                same=positive==window or negative==window
                stats=describe(selected)
                for name in ('mean_v','median_v'):
                    r[f'rolling_{name}_{window}']=stats[name]
                r[f'sign_persistence_{window}']=max(positive,negative)/window
                if same:flags.append(str(window))
                rows.append(dict(dataset=r['dataset'],**group_dict(group_key(r)),sat=r['sat'],
                    frequency_slot=r['frequency_slot'],arc_id=r['arc_id'],
                    segment_id=r['continuous_analysis_segment'],time=r.get('time',''),
                    epoch=int(number(r,'epoch')),window_epochs=window,
                    window_start_epoch=int(number(selected[0],'epoch')),
                    rolling_mean_v=stats['mean_v'],rolling_median_v=stats['median_v'],
                    rolling_std_v=stats['std_v'],rolling_mean_u=stats['mean_u'],
                    positive_ratio=positive/window,negative_ratio=negative/window,
                    sign_persistence=max(positive,negative)/window,
                    consecutive_same_sign_count=streaks[i],candidate_full_window_same_nonzero_sign=int(same),
                    mean_v_squared=stats['mean_v_squared'],
                    variance_around_sample_mean_population=stats['variance_around_sample_mean_population'],
                    mean_pred_var=stats['mean_pred_var'],
                    candidate_noise_raw_second_moment=stats['candidate_noise_raw_second_moment'],
                    candidate_noise_centered_variance=stats['candidate_noise_centered_variance'],
                    squared_mean_inflation=stats['mean_squared_inflation'],
                    state_init_from_current_obs_count=sum(flag(q,'state_init_from_current_obs') for q in selected),
                    phase_d_first_pool=int(r['measurement_class']=='GNSS_CODE'),
                    criterion='COMPLETE_WINDOW_ALL_V_SAME_NONZERO_SIGN__DIAGNOSTIC_CANDIDATE_ONLY'))
            r['persistent_bias_candidate_windows']='|'.join(flags)
    return rows


def summarize_correlations(segments):
    grouped=collections.defaultdict(list)
    for segment in segments: grouped[group_key(segment[0])].append(segment)
    output=[]; evidence=[]
    for segment in segments: evidence.append(segment_evidence(segment))
    for key, arcs in sorted(grouped.items()):
        lengths=[len(a) for a in arcs]
        result=dict(**group_dict(key),nominal_sample_count=sum(lengths),
            continuous_segment_count=len(arcs),segment_length_min=min(lengths),
            segment_length_median=statistics.median(lengths),segment_length_max=max(lengths),
            segments_ge_10=sum(n>=10 for n in lengths),segments_ge_30=sum(n>=30 for n in lengths),
            segments_ge_60=sum(n>=60 for n in lengths),
            state_init_from_current_obs_count=sum(flag(r,'state_init_from_current_obs') for a in arcs for r in a),
            provenance_unknown_count=sum(not flag(r,'provenance_valid') for a in arcs for r in a),
            spp_failed_attempt_count=sum(flag(r,'spp_attempted') and not flag(r,'spp_from_current_obs') for a in arcs for r in a))
        for name in ('v','u'):
            values=[[number(r,name) for r in a] for a in arcs]
            for lag in LAGS:
                terms=[lag_terms(a,lag) for a in values]
                pooled=tuple(sum(t[i] for t in terms) for i in range(4))
                result[f'rho_{name}_{lag}']=rho(pooled)
                result[f'valid_pairs_{name}_{lag}']=pooled[3]
            estimates=[effective_sample_size(a) for a in values]
            qualified=[(len(a),e) for a,(e,_,_) in zip(values,estimates) if e is not None]
            result[f'ESS_{name}_sum_segment_approximations']=sum(e for _,e in qualified) if qualified else None
            result[f'ESS_{name}_nominal_covered']=sum(n for n,_ in qualified)
            result[f'ESS_{name}_segments_covered']=len(qualified)
        result['method']='PER_SEGMENT_MEAN_CENTERED_CROSS_PRODUCTS__NO_CROSS_SEGMENT_PAIRS'
        result['ESS_caveat']='FINITE_LAG_30_INITIAL_POSITIVE_PAIR_APPROXIMATION; CROSS_ARC_INDEPENDENCE_UNPROVEN; NO_LEARNING_FORMULA'
        output.append(result)
    return output,evidence


def phase2_pair_comparison(rows,segments):
    """Reproduce the old per-satellite paired-Pearson statistic for attribution.

    Phase 2 did not form cross-gap pairs, but pooled means from separate arcs.
    This comparison isolates centering and explicitly records changes in pair
    support. A numerical difference alone is not a demonstrated cause.
    """
    track=lambda r:(r['dataset'],r['baseline'],r['sys'],r['signal'],
        r['obs_type'],stage(r),r['sat'])
    tracks=collections.defaultdict(list);arcs=collections.defaultdict(list)
    for r in rows:
        if first(r) and r['measurement_class'] in ('GNSS_CODE','GNSS_PHASE'):
            tracks[track(r)].append(r)
    for segment in segments:arcs[track(segment[0])].append(segment)
    output=[]
    for key,items in sorted(tracks.items()):
        previous=None;pairs=[]
        for r in sorted(items,key=lambda q:number(q,'epoch')):
            good=(r['finite_flag']=='1' and not flag(r,'legacy_reject_flag')
                and not flag(r,'slip_flag') and r['arc_status'] not in
                ('ARC_PENDING_INIT','ARC_REINITIALIZED','UNINITIALIZED')
                and not flag(r,'epoch_failure') and not flag(r,'combined')
                and not flag(r,'inactive_state_support'))
            if (good and previous and number(r,'epoch')==number(previous,'epoch')+1
                    and 0<number(r,'elapsed_s')-number(previous,'elapsed_s')<=1.5):
                pairs.append((previous,r))
            previous=r if good else None
        if len(pairs)<20:continue
        common=[(p,r) for p,r in pairs if p.get('continuous_analysis_segment')
            and p.get('continuous_analysis_segment')==r.get('continuous_analysis_segment')]
        result=dict(zip(('dataset','baseline','sys','signal','obs_type','stage','sat'),key),
            phase2_pairs=len(pairs),common_strict_pairs=len(common),
            strict_continuous_segments=len(arcs[key]),
            strict_segment_length_max=max(map(len,arcs[key]),default=0),
            strict_segment_lengths='|'.join(str(len(s)) for s in arcs[key]))
        byid={segment[0]['continuous_analysis_segment']:segment for segment in arcs[key]}
        for name in ('v','u'):
            result[f'phase2_pair_pooled_rho_{name}']=paired_corr(
                [number(p,name) for p,_ in pairs],[number(r,name) for _,r in pairs])
            result[f'common_pair_pooled_rho_{name}']=paired_corr(
                [number(p,name) for p,_ in common],[number(r,name) for _,r in common])
            means={ident:statistics.fmean(number(r,name) for r in s) for ident,s in byid.items()}
            x=[number(p,name)-means[p['continuous_analysis_segment']] for p,_ in common]
            y=[number(r,name)-means[r['continuous_analysis_segment']] for _,r in common]
            terms=(sum(a*b for a,b in zip(x,y)),sum(a*a for a in x),sum(b*b for b in y),len(x))
            result[f'common_pair_per_segment_centered_rho_{name}']=rho(terms)
            terms=[lag_terms([number(r,name) for r in s],1) for s in arcs[key]]
            result[f'strict_all_pairs_per_segment_centered_rho_{name}']=rho(tuple(sum(t[i] for t in terms) for i in range(4)))
        result['comparison_note']='OLD_PEARSON_POOLS_PAIR_MEANS_ACROSS_SEPARATE_ARCS; COMMON_PAIR_COMPARISON_HOLDS_PAIR_SUPPORT_FIXED'
        output.append(result)
    return output


def bias_candidate_summary(rolling):
    """Small review artifact; every window endpoint remains in validation CSV."""
    grouped=collections.defaultdict(list)
    for r in rolling:grouped[(r['segment_id'],r['window_epochs'])].append(r)
    output=[]
    for (_,window),items in sorted(grouped.items()):
        same=[q for q in items if q['candidate_full_window_same_nonzero_sign']]
        if not same:continue
        representative=max(same,key=lambda q:abs(q['rolling_mean_v']))
        item={k:representative[k] for k in ('dataset','baseline','sys','signal','obs_type',
            'stage','sat','frequency_slot','arc_id','segment_id','window_epochs')}
        item.update(full_windows_examined=len(items),same_sign_candidate_endpoints=len(same),
            candidate_endpoint_fraction=len(same)/len(items),
            first_candidate_time=same[0]['time'],last_candidate_time=same[-1]['time'],
            first_candidate_epoch=same[0]['epoch'],last_candidate_epoch=same[-1]['epoch'],
            rolling_mean_v_min=min(q['rolling_mean_v'] for q in items),
            rolling_mean_v_max=max(q['rolling_mean_v'] for q in items),
            rolling_mean_v_median=statistics.median(q['rolling_mean_v'] for q in items),
            rolling_median_v_median=statistics.median(q['rolling_median_v'] for q in items),
            sign_persistence_median=statistics.median(q['sign_persistence'] for q in items),
            max_consecutive_same_sign_count=max(q['consecutive_same_sign_count'] for q in items),
            representative_time=representative['time'],representative_epoch=representative['epoch'],
            representative_mean_v=representative['rolling_mean_v'],
            representative_median_v=representative['rolling_median_v'],
            representative_std_v=representative['rolling_std_v'],
            representative_mean_u=representative['rolling_mean_u'],
            representative_second_moment=representative['mean_v_squared'],
            representative_centered_variance=representative['variance_around_sample_mean_population'],
            representative_mean_pred_var=representative['mean_pred_var'],
            representative_squared_mean_inflation=representative['squared_mean_inflation'],
            representative_current_obs_init_count=representative['state_init_from_current_obs_count'],
            phase_d_first_pool=representative['phase_d_first_pool'],
            criterion=representative['criterion'])
        output.append(item)
    return output


def annotate(rows):
    for r in rows:
        r['normalized_stage']=stage(r)
        reasons,details,structural=eligibility(r,bool(r.get('persistent_bias_candidate_windows')))
        r['learning_eligibility']='|'.join(reasons) if reasons else 'ELIGIBLE_CANDIDATE'
        r['learning_eligibility_details']='|'.join(details)
        r['structural_survivor']=int(structural)
        r['phase_d_first_pool']=int(r['measurement_class']=='GNSS_CODE' and not flag(r,'combined'))
        r['strict_eligible_candidate']=int(not reasons)


def representative_arcs(correlations,evidence,segments,comparison=(),limit_per_group=3):
    high={tuple(row[k] for k in ('baseline','sys','signal','obs_type','stage'))
        for row in correlations if any(row[f'rho_{name}_1'] is not None and abs(row[f'rho_{name}_1'])>.9 for name in ('v','u'))}
    by_group=collections.defaultdict(list)
    for item in evidence:
        key=tuple(item[k] for k in ('baseline','sys','signal','obs_type','stage'))
        if key in high and item['N']>=10:
            by_group[key].append(item)
    selected=[]
    for key, items in sorted(by_group.items()):
        # Include strongest correlation and longest arc; these answer different
        # questions and avoid choosing only a very short, nearly linear run.
        score=lambda q:max(abs(q.get('rho_v_1') or 0),abs(q.get('rho_u_1') or 0))
        chosen=[]
        for q in [max(items,key=score),max(items,key=lambda q:q['N'])]+sorted(items,key=score,reverse=True):
            if q not in chosen:chosen.append(q)
            if len(chosen)==limit_per_group:break
        selected.extend(chosen)
    # Retain the actual satellites behind the previous approximately .996
    # statistic even if another satellite scores higher after arc centering.
    oldhigh={tuple(q[k] for k in ('dataset','baseline','sys','signal','obs_type','stage','sat'))
        for q in comparison if q['stage']=='STABLE'
        and q['phase2_pair_pooled_rho_u'] is not None and abs(q['phase2_pair_pooled_rho_u'])>.99}
    for key in sorted(oldhigh):
        candidates=[q for q in evidence if tuple(q[k] for k in
            ('dataset','baseline','sys','signal','obs_type','stage','sat'))==key and q['N']>=10]
        if not candidates:continue
        picks=[max(candidates,key=lambda q:q['N']),
            max(candidates,key=lambda q:abs(q['mean_v'])),
            max(candidates,key=lambda q:max(abs(q.get('rho_v_1') or 0),abs(q.get('rho_u_1') or 0)))]
        for q in picks:
            if q not in selected:selected.append(q)
    selected_ids={q['segment_id']:q for q in selected}
    representative=[]
    for arc in segments:
        ident=arc[0]['continuous_analysis_segment']
        if ident not in selected_ids:continue
        summary=selected_ids[ident]
        for r in arc:
            representative.append({k:r.get(k,'') for k in (
                'dataset','baseline','sys','signal','signal2','obs_type','sat','frequency_slot',
                'time','week','tow','epoch','v','u','obs_var','pred_var','Sii','cn0_dbhz',
                'elevation_deg','arc_id','arc_age','continuous_epochs','clock_m','clock_var',
                'isb_m','isb_var','iono_m','iono_var','trop_m','trop_var','ambiguity_m',
                'state_init_from_current_obs','state_init_affects_row','provenance_valid',
                'spp_from_current_obs','spp_attempted','learning_eligibility',
                'continuous_analysis_segment')} | dict(arc_length=summary['N'],
                    arc_rho_v_1=summary['rho_v_1'],arc_rho_u_1=summary['rho_u_1']))
    return representative,selected


def load_rows(paths):
    rows=[]
    inputs=[]
    for path in map(Path,paths):
        with path.open(encoding='utf-8-sig',newline='') as stream:
            reader=csv.DictReader(stream)
            missing=REQUIRED-set(reader.fieldnames or ())
            if missing:raise ValueError(f'{path}: missing Phase 2.5 columns {sorted(missing)}')
            selected=list(reader)
        if any(None in r or None in r.values() for r in selected):
            raise ValueError(f'{path}: CSV column mismatch')
        for row in selected:row['dataset']=path.stem
        rows.extend(selected)
        info=dict(path=str(path.resolve()),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),rows=len(selected))
        reference=ROOT/'validation'/'phase2'/path.name
        if reference.exists() and reference.resolve()!=path.resolve():
            with reference.open(encoding='utf-8-sig',newline='') as stream:
                previous=csv.DictReader(stream);fields=previous.fieldnames
                equal=True;count=0
                for count,old in enumerate(previous,1):
                    if count>len(selected) or any(selected[count-1].get(k)!=old[k] for k in fields):
                        equal=False;break
                equal=equal and count==len(selected)
            info['phase2_reference']=str(reference)
            info['phase2_original_columns_exactly_equal']=equal
            if not equal:raise ValueError(f'{path}: original Phase 2 values or identities changed')
        inputs.append(info)
    return rows,inputs


def analyze_rows(rows, inputs=None):
    """Mutates independent dictionaries only; suitable for deterministic tests."""
    segments,expected=build_segments(rows)
    rolling=rolling_evidence(segments)
    bias_candidates=bias_candidate_summary(rolling)
    annotate(rows)
    correlations,evidence=summarize_correlations(segments)
    comparison=phase2_pair_comparison(rows,segments)
    representatives,selected=representative_arcs(correlations,evidence,segments,comparison)
    grouped=collections.defaultdict(list)
    for r in rows:
        if first(r) and r['measurement_class'] in ('GNSS_CODE','GNSS_PHASE'):
            grouped[group_key(r)].append(r)
    table=[]
    for key,group in sorted(grouped.items()):
        good=[r for r in group if valid(r)]
        s=dict(**group_dict(key),**describe(good),total_first_prefit_rows=len(group),
            invalid_rows=len(group)-len(good),
            structural_survivors=sum(r['structural_survivor'] for r in group),
            strict_eligible_candidates=sum(r['strict_eligible_candidate'] for r in group),
            current_obs_init_rows=sum(flag(r,'state_init_from_current_obs') for r in group),
            current_obs_init_affects_row=sum(flag(r,'state_init_affects_row') for r in group),
            ambiguity_current_obs_init_rows=sum(flag(r,'ambiguity_init_from_current_obs') for r in group),
            persistent_bias_candidate_endpoints=sum(bool(r.get('persistent_bias_candidate_windows')) for r in group),
            lifecycle_counts=json.dumps(dict(collections.Counter(tag for r in group for tag in tags(r))),sort_keys=True),
            exclusion_counts=json.dumps(dict(collections.Counter(tag for r in group for tag in r['learning_eligibility'].split('|') if tag!='ELIGIBLE_CANDIDATE')),sort_keys=True))
        structural=[r for r in good if r['structural_survivor']]
        for k,value in describe(structural).items():s[f'structural_{k}']=value
        pool=[r for r in good if r['strict_eligible_candidate']]
        for k,value in describe(pool).items():s[f'eligible_{k}']=value
        table.append(s)
    counts={}
    for mode in sorted({r['baseline'] for r in rows}):
        mode_rows=[r for r in rows if r['baseline']==mode]
        first_real=[r for r in mode_rows if first(r) and r['measurement_class'] in ('GNSS_CODE','GNSS_PHASE')]
        code=[r for r in first_real if r['measurement_class']=='GNSS_CODE']
        counts[mode]=dict(all_rows=len(mode_rows),first_real_rows=len(first_real),
            code_first_prefit_rows=len(code),
            stable_code_rows=sum(stage(r)=='STABLE' for r in code),
            code_after_startup_arc_init_reject=sum(stage(r)=='STABLE'
                and not tags(r)&INIT_TAGS and not flag(r,'ambiguity_init_from_current_obs')
                and not flag(r,'legacy_reject_flag') for r in code),
            structural_code_survivors=sum(r['structural_survivor'] for r in code),
            strict_eligible_code_candidates=sum(r['strict_eligible_candidate'] for r in code),
            structural_code_groups=len({(r['sys'],r['signal']) for r in code if r['structural_survivor']}),
            strict_eligible_code_groups=len({(r['sys'],r['signal']) for r in code if r['strict_eligible_candidate']}),
            code_current_obs_init_rows=sum(flag(r,'state_init_from_current_obs') for r in code),
            code_current_obs_init_affects_row=sum(flag(r,'state_init_affects_row') for r in code),
            code_provenance_unknown=sum(not flag(r,'provenance_valid') for r in code),
            code_exclusion_reasons=dict(collections.Counter(label for r in code for label in r['learning_eligibility'].split('|'))),
            measurement_classes=dict(collections.Counter(r['measurement_class'] for r in mode_rows)),
            all_eligibility_reasons=dict(collections.Counter(label for r in mode_rows for label in r['learning_eligibility'].split('|'))))
    stable_code_stats=[s for s in table if s['stage']=='STABLE' and s['obs_type']=='P']
    high=[q for q in correlations if any(q[f'rho_{name}_1'] is not None and abs(q[f'rho_{name}_1'])>.9 for name in ('v','u'))]
    summary=dict(inputs=inputs or [],counts=counts,total_stage_group_count=len(table),
        distinct_mode_sys_signal_type_groups=len({(s['baseline'],s['sys'],s['signal'],s['obs_type']) for s in table}),
        distinct_mode_code_signal_groups=len({(s['baseline'],s['sys'],s['signal']) for s in table if s['obs_type']=='P'}),
        stage_groups_with_strict_candidates=sum(s['strict_eligible_candidates']>0 for s in table),
        stage_groups_with_structural_survivors=sum(s['structural_survivors']>0 for s in table),
        expected_cadence_seconds=expected,continuous_segments=len(segments),
        temporal_rows=sum(map(len,segments)),rolling_window_counts=dict(collections.Counter(str(r['window_epochs']) for r in rolling)),
        persistent_full_sign_windows=dict(collections.Counter(str(r['window_epochs']) for r in rolling if r['candidate_full_window_same_nonzero_sign'])),
        high_lag1_groups=high,representative_arc_evidence=selected,
        previous_phase2_high_099_tracks=[q for q in comparison if q['stage']=='STABLE'
            and q['phase2_pair_pooled_rho_u'] is not None and abs(q['phase2_pair_pooled_rho_u'])>.99],
        bias_candidate_segment_window_summaries=len(bias_candidates),
        all_stable_code_moments=stable_code_stats,
        most_inflated_stable_code_groups=sorted(stable_code_stats,key=lambda s:s.get('squared_mean_fraction_of_second_moment') or 0,reverse=True),
        caveats=[
            '44 Phase-2 groups include baseline, observation type and startup/stable split, not 44 independent actual signals.',
            'Structural survivors and normal continuous observation arcs are not independent prediction innovations.',
            'Any state initialized from current observation excludes strict learning, even if outside this row H support.',
            'Persistent full-sign-window evidence is a diagnostic candidate, not a final bias threshold or significance test.',
            'No IID significance test is applied to highly correlated or state-conditioned residuals.',
            'ESS is a finite-lag approximation and cross-satellite/arc independence is not established.',
            'rho is arc-centered normalized lag cross-product, not the biased ACF with complete-arc variance denominator.',
            'code_after_startup_arc_init_reject excludes only those three classes from FIRST_PREFIT code; structural_code_survivors adds validity/gap/slip/reentry/provenance screening.',
            'Negative candidate variance diagnostics are retained, never clipped or fed to R.',
            'GNSS_PHASE is excluded from the first Phase-D pseudorange learning pool.',
            'B effective R, historical penalties and smoothing are audit observations, not fixed-R0 learning input.',
            'All labels and comparisons are offline output only; no Huber, eta, R, Q or reject changes.'])
    return dict(stats=table,bias=rolling,bias_candidates=bias_candidates,
        phase2_pair_comparison=comparison,correlations=correlations,arc_evidence=evidence,
        representatives=representatives,annotated=rows,summary=summary)


def write_csv(path, rows):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    fieldnames=list(dict.fromkeys(k for row in rows for k in row))
    with path.open('w',encoding='utf-8-sig',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=fieldnames)
        writer.writeheader();writer.writerows(rows)


def run(paths, output_dir=DEFAULT_OUT, docs_dir=ROOT/'docs'):
    rows,inputs=load_rows(paths)
    result=analyze_rows(rows,inputs)
    output_dir=Path(output_dir);docs_dir=Path(docs_dir)
    output_dir.mkdir(parents=True,exist_ok=True)
    for name,key in [('INNOVATION_LEARNABILITY_STATS.csv','stats'),
        ('PERSISTENT_BIAS_CANDIDATES.csv','bias_candidates'),('CORRELATION_STATS.csv','correlations')]:
        write_csv(docs_dir/name,result[key])
    for name,key in [('annotated_innovations.csv','annotated'),
        ('representative_arcs.csv','representatives'),('continuous_arc_evidence.csv','arc_evidence'),
        ('rolling_window_evidence.csv','bias'),('phase2_lag1_comparison.csv','phase2_pair_comparison')]:
        write_csv(output_dir/name,result[key])
    (output_dir/'learnability_summary.json').write_text(
        json.dumps(result['summary'],ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('inputs',nargs='*',type=Path)
    parser.add_argument('--output-dir',type=Path,default=DEFAULT_OUT)
    parser.add_argument('--docs-dir',type=Path,default=ROOT/'docs')
    args=parser.parse_args()
    paths=args.inputs or [DEFAULT_OUT/f'{mode}_diag_on.innovation.csv' for mode in ('A','B')]
    result=run(paths,args.output_dir,args.docs_dir)
    print(json.dumps({k:result['summary'][k] for k in ('counts','total_stage_group_count',
        'distinct_mode_sys_signal_type_groups','distinct_mode_code_signal_groups',
        'stage_groups_with_strict_candidates','stage_groups_with_structural_survivors',
        'continuous_segments','temporal_rows')},ensure_ascii=False,indent=2))
