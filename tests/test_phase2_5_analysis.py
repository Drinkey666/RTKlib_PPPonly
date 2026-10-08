"""Synthetic audits for offline Phase 2.5 statistics and continuity boundaries."""
import copy
import csv
import hashlib
import json
import math
from pathlib import Path
import tempfile
import unittest

import analyze_phase2_5 as audit


def observation(epoch, v=None, **changes):
    v = math.sin(epoch*.3) if v is None else v
    row = dict(dataset='synthetic', baseline='A', sys='G', signal='1C', signal2='',
        sat='G01', frequency_slot='0', obs_type='P', measurement_class='GNSS_CODE',
        stage='STEADY', epoch=str(epoch), row='0', trial='0', elapsed_s=str(epoch),
        time=f'T{epoch}', week='0', tow=str(epoch), sample_scope='FIRST_PREFIT',
        v=str(v), u=str(float(v)/2), obs_var='1', pred_var='3', Sii='4', finite_flag='1',
        legacy_reject_flag='0', slip_flag='0', combined='0',
        lifecycle_tags='STABLE|NORMAL_CONTINUOUS', state_init_from_current_obs='0',
        state_init_affects_row='0', ambiguity_init_from_current_obs='0',
        same_epoch_reentry='0', arc_id='1', arc_age=str(epoch),
        continuous_epochs=str(epoch), gap_flag='0', signal_switch_flag='0',
        provenance_valid='1', posterior_committed='1', epoch_failure='0',
        inactive_state_support='0', legacy_current_obs_adjustment='0',
        spp_attempted='0', spp_from_current_obs='0',
        arc_status='ACTIVE', cn0_dbhz='35', elevation_deg='45',
        clock_m='10', clock_var='2', isb_m='0', isb_var='0',
        iono_m='5', iono_var='1', trop_m='2.3', trop_var='.1', ambiguity_m='20')
    row.update({k:str(value) for k,value in changes.items()})
    return row


class MomentTests(unittest.TestCase):
    def test_hand_moments_and_centered_variance(self):
        result=audit.describe([observation(1,1),observation(2,3)])
        self.assertEqual(result['N'],2)
        self.assertEqual(result['mean_v'],2)
        self.assertEqual(result['median_v'],2)
        self.assertAlmostEqual(result['std_v'],math.sqrt(2))
        self.assertAlmostEqual(result['RMS_v'],math.sqrt(5))
        self.assertEqual(result['mean_v_squared'],5)
        self.assertEqual(result['variance_around_sample_mean_population'],1)
        self.assertEqual(result['candidate_noise_raw_second_moment'],2)
        self.assertEqual(result['candidate_noise_centered_variance'],-2)
        self.assertEqual(result['mean_squared_inflation'],4)
        self.assertEqual(result['mean_squared_identity_error'],0)

    def test_positive_negative_zero_ratios(self):
        result=audit.describe([observation(i,v) for i,v in enumerate([-2,0,1,2])])
        self.assertEqual(result['positive_ratio'],.5)
        self.assertEqual(result['negative_ratio'],.25)
        self.assertEqual(result['zero_ratio'],.25)

    def test_stage_never_pooled(self):
        rows=[observation(1,100,stage='STARTUP',lifecycle_tags='STARTUP'),observation(31,1)]
        result=audit.analyze_rows(rows)
        self.assertEqual(len(result['stats']),2)
        means={q['stage']:q['mean_v'] for q in result['stats']}
        self.assertEqual(means,{'STARTUP':100,'STABLE':1})


class EligibilityTests(unittest.TestCase):
    def test_clean_code_eligible(self):
        reasons,details,structural=audit.eligibility(observation(50))
        self.assertEqual(reasons,[]);self.assertEqual(details,[]);self.assertTrue(structural)

    def test_any_current_state_init_excluded_even_outside_H(self):
        r=observation(50,state_init_from_current_obs=1,state_init_affects_row=0)
        reasons,_,structural=audit.eligibility(r)
        self.assertIn('INELIGIBLE_CURRENT_OBS_INIT',reasons)
        self.assertTrue(structural)

    def test_ambiguity_current_init_code_excluded(self):
        r=observation(50,ambiguity_init_from_current_obs=1)
        reasons,_,structural=audit.eligibility(r)
        self.assertIn('INELIGIBLE_ARC_INIT',reasons)
        self.assertIn('INELIGIBLE_CURRENT_OBS_INIT',reasons)
        self.assertFalse(structural)

    def test_code_pending_ambiguity_is_not_repeated_init_event(self):
        r=observation(50,arc_status='ARC_PENDING_INIT')
        self.assertEqual(audit.eligibility(r),([],[],True))
        self.assertTrue(audit.temporal_ok(r))

    def test_phase_retained_for_statistics_not_phase_D_pool(self):
        reasons,details,structural=audit.eligibility(observation(50,
            obs_type='L',measurement_class='GNSS_PHASE'))
        self.assertIn('INELIGIBLE_OTHER',reasons)
        self.assertIn('PHASE_NOT_FIRST_PHASE_D_POOL',details)
        self.assertTrue(structural)

    def test_constraints_and_iflc_separate_exclusions(self):
        reasons,_,_=audit.eligibility(observation(50,
            measurement_class='IONO_PRIOR',signal='',obs_type='PRIOR'))
        self.assertIn('INELIGIBLE_CONSTRAINT',reasons)
        reasons,_,_=audit.eligibility(observation(50,combined=1))
        self.assertIn('INELIGIBLE_IFLC',reasons)

    def test_unknown_provenance_failed_or_invalid_excluded(self):
        for change,detail in [({'provenance_valid':0},'UNKNOWN_INITIALIZATION_PROVENANCE'),
            ({'posterior_committed':0},'EPOCH_NOT_COMMITTED'),
            ({'v':'nan'},'INVALID_INNOVATION'),({'u':'inf'},'INVALID_INNOVATION')]:
            reasons,details,structural=audit.eligibility(observation(50,**change))
            self.assertIn('INELIGIBLE_OTHER',reasons);self.assertIn(detail,details)
            self.assertFalse(structural)

    def test_multiple_lifecycle_exclusions_not_single_precedence(self):
        r=observation(50,stage='STARTUP',slip_flag=1,gap_flag=1,
            legacy_reject_flag=1,trial=1,same_epoch_reentry=1,
            lifecycle_tags='STARTUP|ARC_RESTART|POST_GAP|EDIT_RETRY')
        reasons,_,structural=audit.eligibility(r)
        for name in ('STARTUP','ARC_INIT','SLIP','GAP','REJECT','RETRY'):
            self.assertIn('INELIGIBLE_'+name,reasons)
        self.assertFalse(structural)

    def test_bias_is_candidate_label_not_numeric_threshold(self):
        reasons,_,structural=audit.eligibility(observation(50,1e-12),True)
        self.assertEqual(reasons,['INELIGIBLE_PERSISTENT_BIAS'])
        self.assertTrue(structural)

    def test_B_history_and_effective_R_never_enter_learning_pool(self):
        r=observation(50,baseline='B',R0='.01',obs_var='100')
        reasons,details,structural=audit.eligibility(r)
        self.assertIn('INELIGIBLE_OTHER',reasons)
        self.assertIn('LEGACY_B_RANDOM_MODEL_AND_HISTORY_NOT_FIXED_R0',details)
        self.assertIn('LEGACY_EFFECTIVE_R_DIFFERS_FROM_R0',details)
        self.assertTrue(structural)


class ContinuityTests(unittest.TestCase):
    def test_missing_innovation_breaks_even_raw_arc_same(self):
        rows=[observation(i) for i in (31,32,34,35)]
        segments,_=audit.build_segments(rows)
        self.assertEqual(list(map(len,segments)),[2,2])
        pooled=audit.summarize_correlations(segments)[0][0]
        self.assertEqual(pooled['valid_pairs_v_1'],2)
        self.assertEqual(pooled['valid_pairs_v_2'],0)

    def test_timestamp_gap_breaks_adjacent_epoch(self):
        rows=[observation(i) for i in range(31,38)]
        for r in rows[3:]:r['elapsed_s']=str(float(r['elapsed_s'])+10)
        segments,_=audit.build_segments(rows)
        self.assertEqual(list(map(len,segments)),[3,4])

    def test_signal_return_does_not_rejoin_old_signal(self):
        rows=[observation(31),observation(32),observation(33,signal='5Q'),
            observation(34,signal='5Q'),observation(35),observation(36)]
        segments,_=audit.build_segments(rows)
        self.assertEqual(list(map(len,segments)),[2,2,2])
        self.assertEqual([s[0]['signal'] for s in segments],['1C','5Q','1C'])

    def test_arc_change_slip_reset_reject_all_break(self):
        for changes in [dict(arc_id='2'),dict(slip_flag=1),dict(legacy_reject_flag=1),
            dict(lifecycle_tags='STABLE|ARC_RESTART'),dict(ambiguity_init_from_current_obs=1),
            dict(gap_flag=1),dict(signal_switch_flag=1)]:
            rows=[observation(i) for i in range(31,36)]
            rows[2].update({k:str(v) for k,v in changes.items()})
            segments,_=audit.build_segments(rows)
            self.assertLess(sum(max(0,len(s)-1) for s in segments),4)

    def test_retries_never_duplicate_statistics_or_pairs(self):
        rows=[observation(i) for i in range(31,36)]
        rows.append(observation(33,trial=1,sample_scope='EDIT_RETRY',same_epoch_reentry=1))
        result=audit.analyze_rows(rows)
        self.assertEqual(result['stats'][0]['N'],5)
        self.assertEqual(result['correlations'][0]['valid_pairs_v_1'],4)
        self.assertIn('INELIGIBLE_RETRY',rows[-1]['learning_eligibility'])

    def test_current_obs_init_observed_for_correlation_but_never_learned(self):
        rows=[observation(i,v=i,state_init_from_current_obs=1) for i in range(31,101)]
        result=audit.analyze_rows(rows)
        self.assertEqual(result['correlations'][0]['nominal_sample_count'],70)
        self.assertEqual(result['stats'][0]['structural_survivors'],70)
        self.assertEqual(result['stats'][0]['strict_eligible_candidates'],0)

    def test_unknown_provenance_observed_for_source_audit_never_learned(self):
        rows=[observation(i,v=i,provenance_valid=0) for i in range(31,101)]
        result=audit.analyze_rows(rows)
        self.assertEqual(result['correlations'][0]['nominal_sample_count'],70)
        self.assertEqual(result['correlations'][0]['provenance_unknown_count'],70)
        self.assertEqual(result['stats'][0]['strict_eligible_candidates'],0)

    def test_satellites_never_paired(self):
        rows=[observation(i,sat=sat) for sat in ('G01','G02') for i in range(31,36)]
        segments,_=audit.build_segments(rows)
        self.assertEqual(len(segments),2)
        self.assertEqual(audit.summarize_correlations(segments)[0][0]['valid_pairs_v_1'],8)


class TemporalTests(unittest.TestCase):
    def test_per_segment_centered_manual_correlation(self):
        terms=audit.lag_terms([1,2,3,4],1)
        self.assertEqual(terms,(1.25,2.75,2.75,3))
        self.assertAlmostEqual(audit.rho(terms),5/11)

    def test_between_arc_mean_difference_cannot_manufacture_correlation(self):
        a=[observation(i,10,arc_id=1) for i in range(31,51)]
        b=[observation(i,1000,arc_id=2) for i in range(51,71)]
        segments,_=audit.build_segments(a+b)
        result=audit.summarize_correlations(segments)[0][0]
        self.assertIsNone(result['rho_v_1'])
        self.assertIsNone(result['ESS_v_sum_segment_approximations'])

    def test_long_linear_drift_high_rho_small_effective_count(self):
        values=list(range(100))
        self.assertGreater(audit.rho(audit.lag_terms(values,1)),.99)
        ess,tau,used=audit.effective_sample_size(values)
        self.assertLess(ess,5);self.assertGreater(tau,20)
        self.assertGreater(used,0);self.assertLessEqual(used,30)

    def test_lag30_pairs_require31_continuous_samples(self):
        segments,_=audit.build_segments([observation(i) for i in range(31,61)])
        result=audit.summarize_correlations(segments)[0][0]
        self.assertEqual(result['valid_pairs_v_30'],0)
        self.assertIsNone(result['rho_v_30'])

    def test_full_sign_windows_10_30_60_and_zero_resets_streak(self):
        rows=[observation(i,2) for i in range(31,101)]
        segments,_=audit.build_segments(rows)
        evidence=audit.rolling_evidence(segments)
        counts={w:sum(q['window_epochs']==w for q in evidence) for w in audit.WINDOWS}
        self.assertEqual(counts,{10:61,30:41,60:11})
        self.assertTrue(all(q['candidate_full_window_same_nonzero_sign'] for q in evidence))
        self.assertEqual(rows[8]['persistent_bias_candidate_windows'],'')
        self.assertEqual(rows[9]['persistent_bias_candidate_windows'],'10')
        self.assertEqual(rows[-1]['persistent_bias_candidate_windows'],'10|30|60')
        self.assertEqual(audit.same_sign_streaks([1,1,0,1,-1,-1])[0],[1,2,0,1,1,2])

    def test_sign_alternation_not_persistent_bias_candidate(self):
        rows=[observation(i,(-1)**i) for i in range(31,101)]
        segments,_=audit.build_segments(rows)
        evidence=audit.rolling_evidence(segments)
        self.assertFalse(any(q['candidate_full_window_same_nonzero_sign'] for q in evidence))

    def test_old_pair_mean_pooling_can_inflate_rho_without_cross_gap_pairs(self):
        a=[observation(i,(-1)**i,arc_id=1) for i in range(31,71)]
        b=[observation(i,100+(-1)**i,arc_id=2) for i in range(81,121)]
        rows=a+b;segments,_=audit.build_segments(rows)
        comparison=audit.phase2_pair_comparison(rows,segments)[0]
        self.assertEqual(comparison['phase2_pairs'],78)
        self.assertEqual(comparison['common_strict_pairs'],78)
        self.assertGreater(comparison['phase2_pair_pooled_rho_u'],.99)
        self.assertAlmostEqual(comparison['common_pair_per_segment_centered_rho_u'],-1)
        self.assertEqual(comparison['strict_continuous_segments'],2)

    def test_compact_bias_summary_preserves_all_window_counts(self):
        rows=[observation(i,2) for i in range(31,101)]
        segments,_=audit.build_segments(rows)
        rolling=audit.rolling_evidence(segments)
        summary=audit.bias_candidate_summary(rolling)
        self.assertEqual(len(summary),3)
        self.assertEqual({r['window_epochs']:r['full_windows_examined'] for r in summary},
            {10:61,30:41,60:11})
        self.assertTrue(all(r['candidate_endpoint_fraction']==1 for r in summary))


class FileTests(unittest.TestCase):
    def test_inputs_not_written_outputs_reproducible_and_JSON_finite(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);path=root/'input.csv'
            rows=[observation(i,i,state_init_from_current_obs=1) for i in range(31,101)]
            audit.write_csv(path,rows)
            before=hashlib.sha256(path.read_bytes()).hexdigest()
            a=audit.run([path],root/'out',root/'docs')
            files=list((root/'out').glob('*'))+list((root/'docs').glob('*'))
            first={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
            b=audit.run([path],root/'out',root/'docs')
            self.assertEqual(a['summary'],b['summary'])
            self.assertEqual(before,hashlib.sha256(path.read_bytes()).hexdigest())
            self.assertEqual(first,{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files})
            self.assertEqual(json.loads((root/'out'/'learnability_summary.json').read_text())['stage_groups_with_strict_candidates'],0)

    def test_missing_lifecycle_provenance_contract_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)/'old.csv'
            audit.write_csv(path,[{'baseline':'A','v':'1'}])
            with self.assertRaisesRegex(ValueError,'missing Phase 2.5 columns'):
                audit.load_rows([path])


if __name__=='__main__':
    unittest.main(verbosity=2)
