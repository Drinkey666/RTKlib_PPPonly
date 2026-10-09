"""Offline report checks: reference units and invalid-solution exclusion."""
import unittest
from pathlib import Path
from audit_ppp_accuracy import enu, summary, read_pos, paired

class AccuracyAuditTests(unittest.TestCase):
    def test_reference_origin_and_one_metre_up(self):
        ref=(30.759991,103.984034,482.2020)
        self.assertEqual(enu(*ref,ref),(0.0,0.0,0.0))
        e,n,u=enu(ref[0],ref[1],ref[2]+1.0,ref)
        self.assertAlmostEqual(e,0.0,places=8)
        self.assertAlmostEqual(n,0.0,places=8)
        self.assertAlmostEqual(u,1.0,places=8)

    def test_Q0_excluded_from_error_statistics(self):
        out=Path(__file__).resolve().parents[1]/'validation/accuracy_audit'
        out.mkdir(parents=True,exist_ok=True)
        p=out/'q0_fixture.pos'
        p.write_text('2026/03/21 00:00:00.000 0 0 0 0 0 0 0 0\n'
            '2026/03/21 00:00:01.000 30.759991 103.984034 482.2020 6 8 .1 .1 .1\n',encoding='ascii')
        before=p.read_bytes()
        result,rows=summary('fixture',p,(30.759991,103.984034,482.2020))
        self.assertEqual(result['epochs'],2)
        self.assertEqual(result['valid_epochs'],1)
        self.assertEqual(result['excluded_Q0_epochs'],1)
        self.assertEqual(result['tail60_rms_3d_m'],0.0)
        self.assertEqual(paired('a',rows,'b',rows)['common_valid_epochs'],1)
        self.assertEqual(p.read_bytes(),before)

    def test_ECEF_not_misread_as_lat_lon_degrees(self):
        out=Path(__file__).resolve().parents[1]/'validation/accuracy_audit'
        out.mkdir(parents=True,exist_ok=True)
        p=out/'ecef_fixture.pos'
        p.write_text('2026/03/21 00:00:00.000 -1325716.0 5323471.0 3243306.0 6 8 .1 .1 .1\n',encoding='ascii')
        with self.assertRaisesRegex(ValueError,'expected LLH'):
            read_pos(p)

if __name__=='__main__':unittest.main()
