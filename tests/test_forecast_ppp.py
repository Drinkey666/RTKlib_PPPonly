"""Small contract tests; no positioning truth, tuning or full log copies."""
from datetime import datetime,timedelta
import importlib.util
from pathlib import Path
import json
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('forecast_ppp',ROOT/'tools/forecast_ppp.py')
gate=importlib.util.module_from_spec(spec);spec.loader.exec_module(gate)

class ForecastGateTests(unittest.TestCase):
    def setUp(self):
        self.out=ROOT/'validation/forecast_gate_tests';self.out.mkdir(exist_ok=True)
        self.begin=datetime(2026,3,17,5,33,34);self.end=self.begin+timedelta(minutes=20)
        self.files={k:str(self.out/(k+'.txt')) for k in gate.KEYS}
        for path in self.files.values():Path(path).write_text('fixture\n',encoding='ascii')
        self.files['SP3']=str(self.out/'WUM0MGXNRT_20260742000_02D_05M_ORB.SP3')
        self.files['CLK']=str(self.out/'WUM0MGXNRT_20260742000_02D_05M_CLK.CLK')
        self.write_sp3()
        Path(self.files['CLK']).write_text('PANDA-EXTCLK WHU 20260317 050417 UTC PGM / RUN BY / DATE\nEND OF HEADER\n',encoding='ascii')
        self.receipts={k:dict(received_gpst='2026-03-17 05:00:00',sha256=gate.digest(self.files[k]),evidence='synthetic test receipt') for k in gate.KEYS[1:]}

    def write_sp3(self,orbit='P',clock='P',mixed=False,system='GPS'):
        lines=['%c M  cc '+system+' ccc\n']
        for i in range(12):
            t=datetime(2026,3,17,5,15)+timedelta(minutes=5*i)
            lines.append('*  '+t.strftime('%Y %m %d %H %M')+'  0.00000000\n')
            row=list('PG01'.ljust(80));row[79]=' ' if mixed and i==6 else orbit;row[75]=clock
            lines.append(''.join(row)+'\n')
        Path(self.files['SP3']).write_text(''.join(lines),encoding='ascii')

    def result(self):return gate.audit(self.files,self.receipts,self.begin,self.end,{'G01'})
    def test_valid_prediction_and_receipts(self):self.assertEqual(self.result()['status'],'PASS')
    def test_observed_segment_blocked(self):
        self.write_sp3(' ',' ');self.receipts['SP3']['sha256']=gate.digest(self.files['SP3'])
        self.assertIn('OBS_NOT_IN_PREDICTED_SEGMENT',self.result()['reasons'])
    def test_mixed_segment_blocked(self):
        self.write_sp3(mixed=True);self.assertFalse(self.result()['prediction']['predicted_bracketing_records_only'])
    def test_sp3_clock_without_prediction_blocked(self):
        self.write_sp3(clock=' ');self.assertIn('OBS_NOT_IN_PREDICTED_SEGMENT',self.result()['reasons'])
    def test_filename_does_not_prove_prediction(self):
        self.write_sp3(' ',' ');self.assertIn('NRT',Path(self.files['SP3']).name)
        self.assertFalse(self.result()['prediction']['predicted_bracketing_records_only'])
    def test_missing_receipts_blocked(self):
        self.receipts={};self.assertIn('PRODUCT_AVAILABILITY_NOT_ESTABLISHED',self.result()['reasons'])
    def test_one_future_product_blocks_bundle(self):
        self.receipts['IONEX']['received_gpst']='2026-03-17 06:00:00'
        r=self.result();self.assertEqual(r['status'],'BLOCKED')
        self.assertEqual(next(x for x in r['availability'] if x['product']=='IONEX')['reason'],'FILE_RECEIVED_AFTER_OBSERVATION_START')
    def test_hash_binds_receipt_to_file(self):
        self.receipts['BIA']['sha256']='0'*64;self.assertEqual(self.result()['status'],'BLOCKED')
    def test_receipt_description_required(self):
        del self.receipts['ATX']['evidence'];self.assertEqual(self.result()['status'],'BLOCKED')
    def test_no_local_timezone_in_gpst(self):
        with self.assertRaises(ValueError):gate.gpst('2026-03-17T05:00:00+08:00')
    def test_no_silent_utc_conversion(self):
        with self.assertRaises(ValueError):gate.gpst('2026-03-17T05:00:00Z')
    def test_sp3_other_time_system_explicitly_unsupported(self):
        self.write_sp3(system='UTC')
        with self.assertRaisesRegex(ValueError,'GPS'):self.result()
    def test_missing_satellite_support_not_success(self):
        with self.assertRaises(ValueError):gate.prediction_audit(self.files['SP3'],self.begin,self.end,set())
    def test_outside_coverage_not_success(self):
        with self.assertRaises(ValueError):gate.prediction_audit(self.files['SP3'],self.begin,self.end+timedelta(days=1),{'G01'})
    def test_different_clock_issue_not_success(self):
        old=self.files['CLK'];self.files['CLK']=str(self.out/'WUM0MGXNRT_20260750000_02D_05M_CLK.CLK')
        Path(self.files['CLK']).write_bytes(Path(old).read_bytes())
        self.receipts['CLK']['sha256']=gate.digest(self.files['CLK'])
        self.assertIn('FORECAST_CLK_PROVENANCE_UNCONFIRMED',self.result()['reasons'])
    def test_lsq_clock_not_assumed_prediction(self):
        Path(self.files['CLK']).write_text('PANDA-LSQ WHU PGM / RUN BY / DATE\nEND OF HEADER\n')
        self.assertFalse(self.result()['clock']['extclk_declared'])
    def test_native_window_is_gpst(self):
        text='PPP_CHECK,INFO,OBS,reason=LOADED,records=1200,time_system=GPST,start=2026/03/17 05:33:34.001,end=2026/03/17 05:53:32.998'
        b,e=gate.native_window(text);self.assertEqual(b.hour,5);self.assertEqual(e.minute,53)
    def test_failed_preflight_without_window_not_assumed(self):
        with self.assertRaises(ValueError):gate.native_window('PPP_CHECK,SUMMARY,status=FAIL')
    def test_audit_is_readonly(self):
        before={k:gate.digest(p) for k,p in self.files.items()};self.result()
        self.assertEqual(before,{k:gate.digest(p) for k,p in self.files.items()})

    def exercise_entry(self,availability,mutate=False,source='rinex',cap=0):
        root=self.out/('mock_project_'+self._testMethodName);exe=root/'x64/Release/PPP_only.exe'
        exe.parent.mkdir(parents=True,exist_ok=True);exe.write_bytes(b'synthetic executable placeholder')
        manifest=root/'inputs.json';manifest.write_text(json.dumps(dict(files=self.files,availability=availability,source=source,max_epochs=cap)))
        calls=[];self.environments=[];real_audit=gate.audit
        def fake_run(command,**kwargs):
            calls.append(command)
            self.environments.append(kwargs['env'].copy())
            if '--check-files' in command:
                report=Path(kwargs['env']['RTK_PPP_OUTPUT']+'.products.log')
                report.write_text('PPP_CHECK,INFO,OBS,reason=LOADED,records=1200,time_system=GPST,start=2026/03/17 05:33:34.000,end=2026/03/17 05:53:34.000\nPPP_CHECK,INFO,SATELLITE,reason=AVAILABILITY,sat=G01,epochs=1200\n')
            return subprocess.CompletedProcess(command,0)
        def mutation(*args):
            result=real_audit(*args)
            if mutate:Path(self.files['BIA']).write_text('changed after audit')
            return result
        with patch.object(gate,'ROOT',root),patch.object(sys,'argv',['forecast_ppp',str(manifest),'--run']),patch.object(gate.subprocess,'run',side_effect=fake_run),patch.object(gate,'audit',side_effect=mutation):
            code=gate.main()
        report=sorted((root/'validation/forecast_sessions').glob('*/forecast_session.json'))[-1]
        return code,calls,json.loads(report.read_text(encoding='utf-8'))

    def test_blocked_entry_never_launches_solver(self):
        code,calls,r=self.exercise_entry({})
        self.assertEqual(code,2);self.assertEqual(len(calls),1);self.assertFalse(r['filter_started'])
    def test_passed_entry_uses_same_profile_for_check_and_solver(self):
        code,calls,r=self.exercise_entry(self.receipts)
        self.assertEqual(code,0);self.assertEqual(len(calls),2);self.assertEqual(calls[0][:-1],calls[1])
        self.assertEqual(r['profile'],gate.PROFILE)
    def test_file_mutation_after_check_prevents_solver(self):
        code,calls,r=self.exercise_entry(self.receipts,mutate=True)
        self.assertEqual(code,2);self.assertEqual(len(calls),1);self.assertIn('INPUT_CHANGED_AFTER_AUDIT',r['reasons'])
    def test_txt_entry_uses_txt_environment_only(self):
        code,calls,r=self.exercise_entry({},source='txt-fast',cap=600)
        self.assertEqual(code,2);self.assertIn('--max-epochs',calls[0])
        self.assertNotIn('RTK_PPP_OBS',self.environments[0])
        self.assertEqual(self.environments[0]['RTK_PPP_TXT'],str(Path(self.files['OBS']).resolve()))
    def test_rinex_epoch_cap_is_not_silently_ignored(self):
        with self.assertRaises(SystemExit) as caught:self.exercise_entry({},cap=10)
        self.assertEqual(caught.exception.code,2)

if __name__=='__main__':unittest.main(verbosity=2)
