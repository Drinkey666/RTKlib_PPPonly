"""Preserve completed reports and compact evidence by content hash.
Large native logs/matrices stay in their existing verified locations. No replay,
decompression, product copy, git reset, or production mutation is performed.
"""
from pathlib import Path
import hashlib,json,datetime,sys
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'validation/audit_registry'
COMPACT=(
 'iq_b_30s/latest_run.json','iq_b_30s/latest_metrics.json',
 'k70_forecast/user_requested_b_30s_latest.json',
 'k70_forecast/user_b_30s_20261018_124415_835930/post_startup_60s/summary.json',
 'k70_forecast/user_b_30s_20261018_124415_835930/run.json',
 'k70_forecast/user_b_30s_20261018_124415_835930/run_manifest.json',
 'account_handoff/manifest.json','account_handoff/git_status.txt','account_handoff/git_diff_stat.txt',
 'k70_forecast/solved_metrics.json','k70_forecast/latest_reference_plot.json',
 'k70_forecast/latest_status.json','k70_forecast/rts_bias_audit.json',
 'k70_forecast/rts_nrt_code_bias_overlap.csv',
 'forecast_only/evidence.json','forecast_only/FIN_BLOCKED.inputs.json',
 'forecast_only/NRT_NONPREDICTED_BLOCKED.inputs.json','forecast_only/PREDICTED_BUT_RECEIPTS_UNKNOWN.inputs.json',
 'rapppid_forecast/summary.json','rapppid_forecast/download_receipt.json',
 'rapppid_forecast/NRT_EXISTING_0500/run_receipt.json','rapppid_forecast/NRT_EXISTING_0500/receipt.json',
 'rapppid_forecast/PREDICTED_ORBCLK_07420/run_receipt.json','rapppid_forecast/PREDICTED_ORBCLK_07420/receipt.json',
 'rapppid_k80_plot/metrics.json',
 'joint_prior_transformation/summary.json','joint_prior_transformation/reference_transformed_pairs.csv',
 'joint_prior_transformation/native_inverse_transformed_pairs.csv','joint_prior_transformation/wet_local_conditioning.csv',
 'joint_prior_transformation/reference_existing_wet_history.csv',
 'shared_state_model/summary.json','shared_state_model/completion_checks.json',
 'shared_state_model/native_run.json','shared_state_model/reference_manifest.json','shared_state_model/rapppid_receipt.json',
 'shared_state_model/row_comparison.csv','shared_state_model/epoch_summary.csv','shared_state_model/component_summary.csv',
 'shared_state_model/local_gain_checks.json','shared_state_model/local_gain_effects.csv',
 'shared_state_model/gdv_equation_trial/definition.json','shared_state_model/gdv_equation_trial/response_summary.json',
 'shared_state_model/gdv_equation_trial/period_metrics.csv','shared_state_model/storage_cleanup.json',
 'code_phase_endpoint/summary.json','code_phase_endpoint/directional_fits.csv',
 'code_phase_endpoint/time_split.csv','code_phase_endpoint/arc_inventory.csv',
 'validated_corrections/manifest.json',
 'physical_accuracy/baseline_freeze.json','clock_information_counterfactual/comparison_summary.json',
 'all_code_transfer/causal_summary.json','all_code_transfer/build_evidence.json','all_code_transfer/unit/regression_results.json',
 'code_transfer_components/decomposition.json','product_attitude_audit/summary.json',
 'paired_code_phase/analysis_summary.json','paired_code_phase/build_evidence.json',
 'paired_code_phase/K80_PAIRED.json','paired_code_phase/ACE5_PAIRED.json','paired_code_phase/FINDX6_PAIRED.json',
 'paired_code_phase/gal_split_summary.json','paired_code_phase/rinex_reference_event_checks.json',
 'paired_code_phase/reference_event_medians.json','paired_code_phase/correction_difference_summary.json',
 'paired_code_phase/validation_checks.json','paired_code_phase/reference_event_local_response.json',
 'paired_code_phase/event_counterfactual/definition.json','paired_code_phase/event_counterfactual/response_summary.json',
 'noncombined_joint_batch/summary.json','noncombined_joint_batch/full_record/summary.json',
 'noncombined_joint_batch/relinearized_pass1/summary.json','noncombined_joint_batch/relinearized_pass2/summary.json',
 'noncombined_joint_batch/relinearized_fullpass1/summary.json','noncombined_joint_batch/evidence.json',
 'noncombined_joint_batch/native/build_evidence.json','noncombined_joint_batch/native/pass1/run.json',
 'noncombined_joint_batch/native/pass2/run.json','noncombined_joint_batch/native/fullpass1/run.json',
 'noncombined_joint_batch/completion_checks.json',
 'code_geometry_reference/summary.json','code_geometry_reference/device_summary.json',
 'code_geometry_reference/validation_checks.json','code_geometry_reference/ambiguity_births.json',
 'carrier_information_flow/summary.json','carrier_information_flow/validation_checks.json','carrier_information_flow/storage_cleanup.json',
 'phase_iono_temporal_closure/summary.json','phase_isb_compatibility/summary.json',
 'phase_iono_information_profile/summary.json','full_iono_time_profile/summary.json',
 'full_iono_time_profile/NEW/summary.json','full_iono_time_profile/VIVO_NEW/summary.json',
 'full_iono_gim_drift/summary.json','full_iono_gim_drift/NEW/summary.json','full_iono_gim_drift/VIVO_NEW/summary.json',
 'phase_atmosphere_compatibility/validation_checks.json','phase_atmosphere_compatibility/final_state_comparison.csv',
 'phase_atmosphere_compatibility/geometry_free_prior_tension.csv','phase_atmosphere_compatibility/period_metrics.csv',
 'phase_atmosphere_compatibility/trajectory_limits.csv',
 'iono_time_constraint_sources/summary.json','iono_time_constraint_sources/onset_summary.json',
 'iono_time_constraint_sources/NEW/summary.json','iono_time_constraint_sources/VIVO_NEW/summary.json',
 'iono_time_constraint_sources/NEW/prefix_202/summary.json','iono_time_constraint_sources/VIVO_NEW/prefix_201/summary.json',
 'iono_time_constraint_sources/arc_analysis.json','iono_time_constraint_sources/localized_H_state_support.json',
 'iono_time_constraint_sources/vivo_localized_phase_iono.json','iono_time_constraint_sources/specificity/summary.json',
 'iono_time_constraint_sources/validation_checks.json','iono_time_constraint_sources/storage_cleanup.json',
 'shared_phase_reference/summary.json','colocated_phase_iono/summary.json',
 'iono_affine_evolution/summary.json','iono_affine_evolution/NEW/summary.json','iono_affine_evolution/VIVO_NEW/summary.json',
 'iono_evolution_candidate/summary.json','iono_evolution_candidate/storage_cleanup.json',
 'iono_evolution_candidate/vivo_E29_original_context.csv',
 'iono_affine_native/build_evidence.json','iono_affine_native/unit_results.json',
 'iono_affine_native/verified_v2/build_evidence.json','iono_affine_native/failed_v1/build_evidence.json',
 'iono_affine_native/K80_TREND_V2/run.json','iono_affine_native/VIVO_TREND_V2/run.json',
 'iono_affine_native/VIVO_TREND_RATES/run.json','iono_affine_native/K80_PREFIX120/run.json','iono_affine_native/VIVO_PREFIX120/run.json',
 'iono_affine_native/A_OFF/run.json','iono_affine_native/B_OFF/run.json',
 'iono_affine_native/K80_OFF/run.json','iono_affine_native/VIVO_OFF/run.json',
 'wet_constraint_trial/summary.json','wet_constraint_trial/storage_cleanup.json',
 'wet_constraint_trial/completion_checks.json',
 'wet_constraint_trial/build_evidence.json','wet_constraint_trial/build_triggered_evidence.json',
 'wet_constraint_trial/unit_results.json','wet_constraint_trial/unit_triggered_results.json',
 'wet_constraint_trial/K80_ON/run.json','wet_constraint_trial/VIVO_ON/run.json',
 'wet_constraint_trial/K80_VIOLATION/run.json','wet_constraint_trial/VIVO_VIOLATION/run.json',
 'wet_constraint_trial/K80_OFF/run.json','wet_constraint_trial/VIVO_OFF/run.json',
 'wet_constraint_trial/A_OFF/run.json','wet_constraint_trial/B_OFF/run.json',
 'wet_constraint_trial/A_OFF_TRIGGERED/run.json','wet_constraint_trial/B_OFF_TRIGGERED/run.json',
 'wet_constraint_trial/K80_VIOLATION_PREFIX300/run.json','wet_constraint_trial/VIVO_VIOLATION_PREFIX450/run.json',
 'wet_constraint_trial/K80_VIOLATION_committed_active_events.csv','wet_constraint_trial/VIVO_VIOLATION_committed_active_events.csv',
 'diagnostic_storage_manifest.json')
DIAGNOSTIC_SOURCES=(
 'diagnose_b_continuous_information.py','trace_b_committed_information.py','analyze_b_continuous_information.py',
 'trial_rinex_phase_identity.py','test_rinex_phase_identity.py','trial_phase_reference_seed.py',
 'phase_reference_seed_regression.c','check_colocated_code_reference.py','report_b_continuous_information.py',
 'diagnose_b_startup.py','trial_b_initialization_continuity.py','check_b_startup_findings.py',
 'b_iono_continuity_regression.c','report_b_startup_followup.py',
 'four_sample_diagnosis.py','audit_four_sample_input.py','audit_four_sample_clock_reference.py',
 'build_four_sample_policy_probe.py','report_four_sample_diagnosis.py','verify_b_reference_causality.py',
 'four_sample_iono_lifecycle_regression.c','four_sample_reference_regression.c',
 'test_four_sample_iono_lifecycle.py','archive_four_sample_logs.py',
 'process_iq_b_30s.py','report_iq_b_30s.py',
 'run_k70_user_b_30s.py','report_k70_user_b_30s.py','plot_k70_post_startup.py',
 'capture_codex_handoff.py','k70_reference_projection.py','report_k70_forecast_processing.py',
 'prepare_k70_forecast_processing.py','audit_k70_bias_products.py','download_k70_vmf_authenticated.py',
 'test_forecast_ppp.py','test_forecast_session_integration.py',
 'run_rapppid_forecast.py','replay_rapppid_forecast.m','report_rapppid_forecast.py',
 'plot_rapppid_k80_convergence.py',
 'audit_joint_prior_transformation.py','export_reference_wet_history.m',
 'run_shared_state_model_probe.py','run_shared_state_rapppid.py','probe_shared_state_rapppid.m','shared_state_evaluate.m',
 'analyze_shared_state_models.py','check_shared_state_local_gains.py','trial_shared_state_gdv.py','report_shared_state_models.py',
 'audit_code_phase_endpoint.py',
 'check_shared_phase_reference.py','check_colocated_phase_iono.py','trial_iono_affine_evolution.py',
 'iono_affine_trial_kernel.c','build_iono_affine_native_trial.py','iono_affine_native_regression.c',
 'run_iono_affine_native_tests.py','run_iono_affine_native_replay.py','analyze_iono_evolution_candidate.py',
 'wet_constraint_trial_kernel.c','wet_constraint_regression.c','build_wet_constraint_trial.py',
 'run_wet_constraint_tests.py','run_wet_constraint_replay.py','analyze_wet_constraint_trial.py')


def main(verify=False, selected=None):
    OUT.mkdir(exist_ok=True);snap=OUT/'snapshots';snap.mkdir(exist_ok=True);manifest=OUT/'AUDIT_REGISTRY.json'
    records=json.loads(manifest.read_text(encoding='utf-8')) if manifest.exists() else []
    if not verify and selected is None:
        files=sorted((ROOT/'docs').glob('*.md'))+[ROOT/'validation'/p for p in COMPACT if (ROOT/'validation'/p).exists()]
        files += [ROOT/'tests'/p for p in DIAGNOSTIC_SOURCES if (ROOT/'tests'/p).exists()]
        files += [ROOT/p for p in ('PROJECT_HANDOFF.md','NEW_CODEX_PROMPT.md',
            'tools/forecast_ppp.py','run_forecast_ppp.cmd',
            'config/forecast_products.example.json') if (ROOT/p).exists()]
        if (ROOT/'AGENTS.md').exists():files.append(ROOT/'AGENTS.md')
        files += [ROOT/'run_b_reference_candidate.cmd',ROOT/'docs/FOUR_SAMPLE_CONTROLLED_METRICS.csv']
        files += [ROOT/'docs/B_STARTUP_CONTINUITY_RESULTS.csv',ROOT/'docs/B_STARTUP_FIRST60.png']
        files += [ROOT/'docs/B_CONTINUOUS_INFORMATION_RESULTS.csv',ROOT/'docs/B_CONTINUOUS_INFORMATION.png']
        for dirname in ('b_continuous_information','rinex_phase_identity','phase_reference_seed'):
            task=ROOT/'validation'/dirname
            files += list(task.glob('*.json'))+list(task.glob('*/run.json'))+list(task.glob('*/metrics.json'))
            for pattern in ('build/*.c','build/*.json','committed_build/*.c','committed_build/*.json'):
                files += list(task.glob(pattern))
        task=ROOT/'validation/b_continuous_information'
        files += [task/p for p in ('selected_updates.csv','selected_group_effects.csv','interval_information_accounting.csv','phase_state_timeline.csv','posterior_state_correlations.csv','instantaneous_geometry.csv')]
        for dirname in ('b_startup_diagnosis','b_initialization_continuity'):
            task=ROOT/'validation'/dirname
            files += list(task.glob('*.json'))+list(task.glob('*.csv'))
            files += list(task.glob('*/run.json'))+list(task.glob('*/metrics.json'))
            files += list(task.glob('build/unit_results.json'))+list(task.glob('build/unit_build.cmd'))
        task=ROOT/'validation/four_sample_diagnosis'
        files += list(task.glob('*.json'))+list(task.glob('*/run.json'))+list(task.glob('*/metrics.json'))
        for pattern in ['private*/*.c','private*/build*.json','private*/unit_results.json','prefix120/*/result.json']:
            files += list(task.glob(pattern))
        task=ROOT/'validation/verified_integration'
        if task.exists():
            files += list(task.glob('*.json'))+list(task.glob('*.patch'))+list(task.glob('*.csv'))
            files += list(task.glob('**/run.json'))+list(task.glob('**/metrics.json'))
            for rel in ['final/replay_results.json','exact_code_final/summary.json',
                        'exact_code_final/build.json','exact_code_final/contrasts.csv',
                        'ordinary_robust_verified/summary.json','ordinary_robust_verified/build.json',
                        'ordinary_robust_verified/accepted_weights.json','ordinary_robust_verified/unit_results.json',
                        'ordinary_robust/ABANDONED.json']:
                if (task/rel).exists():files.append(task/rel)
            for rel in ['verify_verified_integration.py','verified_profile_regression.c',
                        'replay_verified_integration.py','exact_paired_code_model.c',
                        'run_exact_paired_code_model.py','trial_verified_ordinary_robust.py',
                        'verified_ordinary_robust_regression.c','report_verified_integration.py']:
                files.append(ROOT/'tests'/rel)
            for rel in ['src/ppp.c','src/rinex.c','src/smartphone_ppp_config.c','src/smartphone_ppp_config.h',
                        'src/rnx2rtkp.c','src/gnss_replay.c','PPP_only/ppp_position.c',
                        'run_b_verified.cmd','run_b_legacy.cmd',
                        'docs/VERIFIED_B_INTEGRATION_METRICS.csv','docs/VERIFIED_B_INTEGRATION.png','docs/VERIFIED_B_AFTER60.png']:
                files.append(ROOT/rel)
        task=ROOT/'validation/remaining_code_state'
        if task.exists():
            files += list(task.glob('*.json'))+list(task.glob('*.csv'))
            files += list(task.glob('**/run.json'))+list(task.glob('common_mode/build/*.json'))
            files += [task/'common_mode/build/ppp.c',ROOT/'docs/PPP_COMMON_CLOCK_MASKING.png']
            for rel in ['diagnose_remaining_code_state.py','diagnose_common_clock_masking.py',
                        'analyze_common_clock_masking.py','audit_oct18_frequency_support.py','report_common_clock_masking.py']:
                files.append(ROOT/'tests'/rel)
        task=ROOT/'validation/correlated_huber'
        if task.exists():
            files += list(task.glob('*.json'))+list(task.glob('*.csv'))+list(task.glob('*/run.json'))
            files += list(task.glob('*/metrics.json'))+list(task.glob('**/results.json'))+list(task.glob('**/evidence.json'))
            files += [task/'build/ppp.c',task/'covariance_probe/build/ppp.c']
            for rel in ['trial_correlated_huber.py','conditional_huber_kernel.h','conditional_huber_regression.c',
                        'test_conditional_huber.py','test_correlated_huber_snapshots.py','probe_correlated_covariance.py','report_correlated_huber.py']:
                files.append(ROOT/'tests'/rel)
            files += list((ROOT/'docs').glob('CORRELATED_HUBER*.png'))
        for dirname in ['b_covariance_symmetry','k70_weight_slowdown','conditional_evidence_audit','b_joseph_integration','joint_huber']:
            task=ROOT/'validation'/dirname
            if task.exists():
                files += list(task.glob('*.json'))+list(task.glob('*.csv'))+list(task.glob('**/evidence.json'))
                files += list(task.glob('**/run.json'))+list(task.glob('**/results.json'))
                for pattern in ['*.patch','unit/*.results.txt','real_checks/*.c','build/*.c','joseph_trial/build/*.c','joseph_trial/unit/*.c','joseph_trial/unit/*.cmd','joseph_trial/*.json','joseph_trial/*.csv','startup/build/*.c']:
                    files += list(task.glob(pattern))
        for rel in ['audit_conditional_evidence.py','report_conditional_evidence.py',
                    'diagnose_b_covariance_symmetry.py','complete_formal_b_symmetry.py','analyze_b_covariance_symmetry.py',
                    'check_b_covariance_decimal.py','trial_b_joseph_symmetry.py','capture_k70_weight_slowdown.py',
                    'capture_k70_startup_weights.py','analyze_k70_weight_slowdown.py','report_b_covariance_followup.py']:
            files.append(ROOT/'tests'/rel)
        files.append(ROOT/'docs/K70_LATE_WEIGHT_BRIDGE.png')
        files.append(ROOT/'docs/CONDITIONAL_EVIDENCE_SCORES.png')
        files += [ROOT/'tests'/p for p in ['replay_b_joseph_integration.py', 'verify_b_joseph_integration.py', 'joint_huber_kernel.h', 'joint_huber_regression.c', 'trial_joint_huber.py', 'test_joint_huber_snapshots.py', 'report_joint_huber.py']]
        files += [ROOT/p for p in ['src/rtkcmn.c','src/rtklib.h','docs/JOINT_HUBER_FULL.png','docs/JOINT_HUBER_K70_LATE.png']]
        task=ROOT/'validation/huber_state_ambiguity'
        files += list(task.glob('*.json'))+list(task.glob('*.csv'))+list(task.glob('**/run.json'))+list(task.glob('**/metrics.json'))
        files += list(task.glob('**/evidence.json'))+list(task.glob('**/results.json'))+list(task.glob('**/summary.json'))
        files += list(task.glob('**/probe.c'))+list(task.glob('**/tests.c'))+list(task.glob('**/ppp.c'))
        files += [ROOT/'tests'/p for p in ['diagnose_huber_state_ambiguity.py', 'check_huber_wet_physicality.py', 'b_wet_feasibility_adapter.h', 'test_b_wet_feasibility.py', 'trial_b_wet_feasibility.py', 'finish_b_wet_feasibility.py', 'report_huber_state_diagnosis.py']]
        files.append(ROOT/'docs/HUBER_STATE_FEASIBILITY.png')
        task=ROOT/'validation/k70_history_state'
        files += list(task.glob('*.json'))+list(task.glob('*.csv'))
        files += [ROOT/p for p in ['tests/decompose_k70_history_state.py','tests/report_k70_history_state.py','docs/K70_HISTORY_STATE.png']]
        task=ROOT/'validation/temporal_code_identifiability'
        files += list(task.glob('*.json'))+list(task.glob('*.csv'))
        files += [ROOT/'tests'/p for p in ['audit_temporal_code_identifiability.py','report_temporal_code_identifiability.py']]
        task=ROOT/'validation/gnss_redundancy'
        files += list(task.glob('*.json'))+list(task.glob('*.csv'))+list(task.glob('*.csv.gz'))
        files += [ROOT/'tests'/p for p in ['gnss_redundancy_evidence.py','test_gnss_redundancy_evidence.py','evaluate_gnss_redundancy.py','report_gnss_redundancy.py']]
        task=ROOT/'validation/joint_prior_observation'
        files += list(task.glob('*.json'))+list(task.glob('*.csv'))+list(task.glob('*.txt'))
        files += [ROOT/'tests'/p for p in ['joint_prior_observation_trial.py','test_joint_prior_observation.py','evaluate_joint_prior_observation.py','report_joint_prior_observation.py']]
        task=ROOT/'validation/k70_prior_full'
        files += list(task.glob('*.json'))+list(task.glob('*.csv'))+list(task.glob('*/run.json'))+list(task.glob('*/metrics.json'))+list(task.glob('build/*.json'))
        for rel in ['build/ppp.c','build/smartphone_ppp_config.c','build/probe.c','build/joint_prior_cutoffs.h','build/link.rsp']:
            files.append(task/rel)
        files += [ROOT/'tests'/p for p in ['joint_prior_replay_kernel.h','replay_k70_prior_trial.py','check_k70_prior_native.py','report_k70_prior_full.py']]
        files += [ROOT/'docs'/p for p in ['K70_PRIOR_FULL_CURVES.png','K70_PRIOR_FULL_ZWD.png']]
        task=ROOT/'validation/four_sample_data_quality'
        files += list(task.glob('*.json'))+list(task.glob('*.csv'))
        files += [ROOT/'tests'/p for p in ['audit_four_sample_data_quality.py','check_raw_quality_events.py','report_four_sample_data_quality.py']]
        files.append(ROOT/'docs/FOUR_SAMPLE_DATA_QUALITY.png')
        task=ROOT/'validation/g32_qc_decisions'
        files += list(task.glob('*.json'))+list(task.glob('*/*.json'))+list(task.glob('*/*.csv'))
        files.append(ROOT/'tests/audit_g32_qc_decisions.py')
        task=ROOT/'validation/recovery_code_bridge'
        files += list(task.glob('*.json'))+list(task.glob('*.csv'))
        files.append(ROOT/'tests/check_recovery_code_bridge.py')
        task=ROOT/'validation/recovery_code_qc'
        files += list(task.glob('*.json'))+list(task.glob('*.csv'))+list(task.glob('*/*.json'))
        files += [task/'build/ppp.c',task/'build/rinex.c',task/'build/link.rsp']
        files += [ROOT/'tests'/p for p in ['recovery_code_qc_kernel.h','recovery_code_qc_adapter.h','recovery_code_qc_regression.c','trial_recovery_code_qc.py','verify_recovery_code_qc.py','report_recovery_code_qc.py']]
        files += [ROOT/'run_recovery_code_trial.cmd',ROOT/'docs/RECOVERY_CODE_QC_FULL.png',ROOT/'docs/RECOVERY_CODE_QC_AFTER60.png']
        files += [ROOT/'tests/organize_generated_evidence.py',ROOT/'tests/build_project_continuation.py']
        files += list((ROOT/'validation/project_organization').glob('*.json'))
        files += [ROOT/'PROJECT_CONTINUATION'/p for p in ['MANIFEST.json','CURRENT_STATE.json','EXPERIMENT_INDEX.csv','EXPERIMENT_DECISIONS.json','CODEX_PROMPT.md']]
        task=ROOT/'validation/external_station_joint_filter_v1'
        if task.exists():
            files += list(task.glob('*.json'))+list(task.glob('*.csv'))
            files += list(task.glob('*/run.json'))+list(task.glob('product_drift/*.json'))
            files += list(task.glob('product_drift/matched_product_changes.csv'))
            files += [task/'build/manifest.json',task/'wet_observer/build.json']
            files += [ROOT/'tests'/p for p in ['trial_external_station_joint_filter.py',
                'observe_external_station_wet_update.py','audit_external_station_product_drift.py',
                'check_external_station_joint_filter.py']]
            files += [ROOT/'docs'/p for p in ['EXTERNAL_STATION_JOINT_FILTER.png','EXTERNAL_STATION_WET_DELAY.png']]
        task=ROOT/'validation/external_station_phase_closure_v1'
        if task.exists():
            files += list(task.glob('*.json'))+list(task.glob('*.csv'))
            files += list(task.glob('prefix4/run.json'))+list(task.glob('build/manifest.json'))
            files += [ROOT/'tests'/p for p in ['audit_external_station_phase_closure.py',
                'analyze_external_phase_state_closure.py','fit_external_phase_temporal_model.py',
                'capture_external_station_prefix4.py','profile_external_station_prefix4.py','check_external_phase_closure.py']]
            files += [ROOT/'docs/EXTERNAL_PHASE_STATE_CAUSAL.png']
        # Completed 10/26 private trials and tracking evidence. Keep large logs,
        # executable/object files and original inputs in place, only snapshot
        # compact receipts, sources and figures here.
        task=ROOT/'validation/iono_observable_rate_v1'
        if task.exists():
            files += list(task.glob('*.json'))+list(task.glob('*.csv'))
            files += list(task.glob('*/run.json'))+list(task.glob('*/manifest.json'))
            files += [p for p in (task/'android_receipts').glob('*') if p.is_file()]
            files += [ROOT/'tests'/p for p in ['iono_observable_rate_gate.h','iono_forecast_reference.h',
                'build_iono_observable_rate_trial.py','build_iono_forecast_rate_trial.py',
                'iono_observable_rate_regression.c','test_iono_observable_rate.py',
                'replay_iono_observable_rate.py','analyze_iono_observable_rate.py',
                'audit_oct25_slip_attribution.py','finish_iono_tracking_evidence.py']]
            files += [ROOT/'docs/IONO_OBSERVABLE_RATE_FULL.png']
        for dirname in ['oct25_slip_attribution_v1','oct25_tracking_probe_v1']:
            task=ROOT/'validation'/dirname
            files += list(task.glob('*.json'))+list(task.glob('*.csv'))
        for dirname in ['mar17_default_comparison_v1','mar17_nrt_rts_noncombined_v1']:
            task=ROOT/'validation'/dirname
            files += list(task.glob('*.json'))+list(task.glob('*.csv'))+list(task.glob('*/run.json'))
            files += list(task.glob('failed_output_v1/*.json'))
        files += [ROOT/'tests'/p for p in ['snapshot_rapppid_factory_defaults.m','run_mar17_default_comparison.py',
            'replay_mar17_factory_defaults.m','report_mar17_default_comparison.py',
            'run_mar17_nrt_rts_comparison.py','replay_mar17_nrt_rts_noncombined.m','report_mar17_nrt_rts_comparison.py']]
        files += [ROOT/'docs/MAR17_NRT_RTS_NONCOMBINED.png']
        task=ROOT/'validation/k70_all_nrt_rts_east_v1'
        if task.exists():
            files += list(task.glob('*.json'))+list(task.glob('*.csv'))+list(task.glob('*/run.json'))
            files += [ROOT/'tests'/p for p in ['run_k70_all_nrt_rts.py','report_k70_all_nrt_rts.py']]
            files += [ROOT/'docs/K70_ALL_NRT_RTS_EAST.png']
        task=ROOT/'validation/acquisition_code_phase_repair_v1'
        if task.exists():
            files += list(task.glob('*.json'))+list(task.glob('*.csv'))+list(task.glob('*.patch'))
            files += list(task.glob('replay/*.json'))+list(task.glob('replay/fault_injection.csv'))
            files += list(task.glob('paper_both_negative_control/*.json'))+list(task.glob('paper_both_negative_control/fault_injection.csv'))
            files += list(task.glob('android_source/**/*.kt'))+[ROOT/'tests/acquisition_code_phase_repair_summary.py']
        task=ROOT/'validation/fullbias_reference_v1'
        if task.exists():
            files += list(task.glob('*.json'))+list(task.glob('*.csv'))+list(task.glob('*.h'))+list(task.glob('*.kt'))
            files += [ROOT/'tests/audit_fullbias_conversion.py',ROOT/'tests/fullbias_adapter_probe.c']
        task=ROOT/'validation/fullbias_reference_fix_v1'
        if task.exists():
            files += list(task.glob('*.json'))+list(task.glob('*.csv'))+list(task.glob('*/run.json'))+list(task.glob('build_v3/manifest.json'))
            files += list(task.glob('source/**/*.*'))+[ROOT/'docs/FULLBIAS_REFERENCE_FIX_CURVES.png']
            files += [ROOT/p for p in ['tests/fullbias_clock_reference_trial.h','tests/fullbias_clock_reference_probe.c',
                'tests/build_fullbias_reference_fix.py','tests/run_fullbias_reference_fix.py','tests/report_fullbias_reference_fix.py',
                'tools/run_clock_reference_candidate.py','run_clock_reference_candidate.cmd']]
    if not verify:
        if selected is not None:
            files=[(ROOT/p).resolve(strict=True) for p in selected]
            if any(not p.is_relative_to(ROOT) for p in files):
                raise ValueError('Selected audit files must be inside the project')
        known={(r['path'],r['sha256']) for r in records}
        for p in files:
            payload=p.read_bytes();h=hashlib.sha256(payload).hexdigest();key=(str(p.relative_to(ROOT)),h)
            if key in known:continue
            target=snap/(h+p.suffix)
            if not target.exists():
                with target.open('xb') as f:f.write(payload)
            assert target.read_bytes()==payload
            records.append(dict(path=key[0],sha256=h,bytes=len(payload),snapshot=str(target.relative_to(ROOT)),
                recorded_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
        temporary=OUT/'AUDIT_REGISTRY.tmp';temporary.write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8');temporary.replace(manifest)
    selected_keys={str(p.relative_to(ROOT)) for p in files} if selected is not None and not verify else None
    verification=records if selected_keys is None else [r for r in records if r['path'] in selected_keys]
    for r in verification:
        p=(ROOT/r['snapshot']).resolve(strict=True);assert p.is_relative_to(snap.resolve())
        assert hashlib.sha256(p.read_bytes()).hexdigest()==r['sha256'],r['path']
    result=dict(preserved_versions=len(records),snapshot_bytes=sum(r['bytes'] for r in records))
    if selected_keys is None:result['all_snapshot_hashes_valid']=True
    else:result.update(verified_selected_versions=len(verification),selected_snapshot_hashes_valid=True)
    print(json.dumps(result))


if __name__=='__main__':main(sys.argv[1:]==['--verify'])
