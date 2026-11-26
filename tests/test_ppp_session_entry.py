"""Real entry safety contracts: mixed modes, stale environment and output safety."""
import sys,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import run_ppp_session as entry
from ppp_preset import environment,PROFILE

class SessionEntryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.exe=self.root/'x64/Release/PPP_only.exe';self.exe.parent.mkdir(parents=True);self.exe.write_bytes(b'fixture')
        trial=self.root/'validation/recovery_session/build/trial.exe';trial.parent.mkdir(parents=True);trial.write_bytes(b'trial')
        self.files={k:str(self.root/(k+'.txt')) for k in entry.PRODUCTS|{'OBS'}}
        for p in self.files.values():Path(p).write_text('fixture')
        self.files['SP3']=str(self.root/'WUM0MGXNRT_20262900000_02D_05M_ORB.SP3');Path(self.files['SP3']).write_text('orbit fixture')
        self.files['CLK']=str(self.root/'WUM0MGXNRT_20262900000_02D_30S_CLK.CLK');Path(self.files['CLK']).write_text('PANDA-EXTCLK WHU PGM / RUN BY / DATE\nEND OF HEADER\n')
        self.manifest={'source':'rinex','files':self.files};self.output=self.root/'new.pos'
        self.patcher=patch.object(entry,'ROOT',self.root);self.patcher.start()
    def tearDown(self):self.patcher.stop();self.tmp.cleanup()
    def plan(self,**kwargs):return entry.plan(self.manifest,self.output,**kwargs)
    def test_forecast_gate_and_session_share_formal_profile(self):
        import forecast_ppp
        self.assertEqual(PROFILE,forecast_ppp.PROFILE);self.assertEqual(PROFILE['PROFILE'],'B_VERIFIED');self.assertEqual(PROFILE['GLO'],'0')
    def test_stale_model_environment_removed(self):
        parent={'PATH':'ok','RTK_PPP_PROFILE':'DEFAULT','RTK_PPP_OPTS':'-BAD=1','RTK_PPP_CODE_RECOVERY':'BRIDGE3','rtk_ppp_audit_policy':'BAD'}
        _,env=self.plan(parent=parent);self.assertEqual(env['PATH'],'ok');self.assertEqual(env['RTK_PPP_PROFILE'],'B_VERIFIED')
        self.assertFalse(any(k in env for k in ['RTK_PPP_OPTS','RTK_PPP_CODE_RECOVERY','rtk_ppp_audit_policy']))
    def test_formal_exe_is_default(self):
        r,_=self.plan();self.assertEqual(Path(r['executable']),self.exe);self.assertEqual(r['recovery'],'OFF')
    def test_explicit_recovery_selects_separate_exe(self):
        r,e=self.plan(recovery=True);self.assertIn('recovery_session',r['executable']);self.assertEqual(e['RTK_PPP_CODE_RECOVERY'],'BRIDGE3')
    def test_no_environment_mutation(self):
        parent={'RTK_PPP_OPTS':'old'};self.plan(parent=parent);self.assertEqual(parent,{'RTK_PPP_OPTS':'old'})
    def test_effective_inputs_hashed(self):
        r,_=self.plan();self.assertEqual(set(r['input_sha256']),set(self.files))
    def test_truth_not_an_allowed_input(self):
        self.files['REFERENCE']='not allowed'
        with self.assertRaises(ValueError):self.plan()
    def test_model_overrides_rejected(self):
        self.manifest['profile']='PHYSICAL'
        with self.assertRaises(ValueError):self.plan()
    def test_existing_output_rejected(self):
        self.output.write_text('trusted old output')
        with self.assertRaises(ValueError):self.plan()
        self.assertEqual(self.output.read_text(),'trusted old output')
    def test_existing_sidecar_rejected(self):
        Path(str(self.output)+'.trace').write_text('old trace')
        with self.assertRaises(ValueError):self.plan()
    def test_existing_events_file_rejected(self):
        self.output.with_name(self.output.stem+'_events.pos').write_text('old events')
        with self.assertRaises(ValueError):self.plan()
    def test_compressed_old_trace_rejected(self):
        Path(str(self.output)+'.trace.gz').write_bytes(b'old evidence')
        with self.assertRaises(ValueError):self.plan()
    def test_output_cannot_overwrite_input(self):
        self.output=Path(self.files['OBS'])
        with self.assertRaises(ValueError):self.plan()
    def test_missing_input_is_error(self):
        Path(self.files['BIA']).unlink()
        with self.assertRaises(FileNotFoundError):self.plan()
    def test_both_observation_sources_rejected(self):
        self.files['TXT']=self.files['OBS']
        with self.assertRaises(ValueError):self.plan()
    def test_txt_has_no_rinex_environment(self):
        self.manifest['source']='txt-fast';self.files['TXT']=self.files.pop('OBS')
        r,e=self.plan();self.assertNotIn('RTK_PPP_OBS',e);self.assertIn('RTK_PPP_TXT',e);self.assertEqual(r['source'],'txt-fast')
    def test_unknown_source_rejected(self):
        self.manifest['source']='live-ssr'
        with self.assertRaises(ValueError):self.plan()
    def test_epoch_cap_not_silently_ignored(self):
        self.manifest['max_epochs']=60
        with self.assertRaises(ValueError):self.plan()
    def test_unknown_override_not_silently_ignored(self):
        self.manifest['Q_clock']=10
        with self.assertRaises(ValueError):self.plan()
    def test_cannot_claim_live_by_changing_manifest_label(self):
        self.manifest['usage']='LIVE_FORECAST'
        with self.assertRaises(ValueError):self.plan()
    def test_mismatched_clock_issue_rejected(self):
        p=self.root/'WUM0MGXNRT_20262900100_02D_30S_CLK.CLK';p.write_text(Path(self.files['CLK']).read_text());self.files['CLK']=str(p)
        with self.assertRaises(ValueError):self.plan()
    def test_nonforecast_clock_rejected(self):
        Path(self.files['CLK']).write_text('PANDA-LSQ WHU PGM / RUN BY / DATE\nEND OF HEADER\n')
        with self.assertRaises(ValueError):self.plan()
    def test_archived_regression_does_not_claim_clock_prediction(self):
        Path(self.files['CLK']).write_text('PANDA-CLKDEN WHU PGM / RUN BY / DATE\nEND OF HEADER\n')
        self.manifest['usage']='ARCHIVED_REGRESSION';r,_=self.plan()
        self.assertFalse(r['clock_forecast_provenance']['extclk_declared']);self.assertEqual(r['usage'],'ARCHIVED_REGRESSION')
    def test_no_files_written_in_prepare(self):
        before={p for p in self.root.rglob('*')};self.plan();self.assertEqual(before,{p for p in self.root.rglob('*')})

if __name__=='__main__':unittest.main(verbosity=2)
