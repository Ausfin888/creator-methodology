from pathlib import Path
import ast, importlib.util, json, shutil, subprocess, sys, tempfile, unittest
ROOT=Path(__file__).resolve().parents[1]
S=ROOT/'scripts'
sys.path.insert(0,str(S))
from audit_caps import assess
from subtitle_utils import read_cues
from transcribe import ts
class Checks(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.d=Path(self.temp.name)
    def tearDown(self): self.temp.cleanup()
    def run_script(self,name,*args):
        return subprocess.run([sys.executable,str(S/name),*map(str,args)],capture_output=True,text=True)
    def data(self):
        for p in (ROOT/'examples/input').glob('*'):
            if p.name.endswith(('.srt','.info.json')): shutil.copy2(p,self.d/p.name)
    def notes(self):
        shutil.copytree(ROOT/'examples/output',self.d/'out')
        return self.d/'out'
    def test_syntax_all(self):
        for p in S.glob('*.py'): ast.parse(p.read_text(),filename=str(p))
    def test_help_without_mlx_dependencies(self):
        for p in S.glob('*.py'):
            if p.name!='subtitle_utils.py': self.assertEqual(self.run_script(p.name,'--help').returncode,0,p.name)
    def test_audit_unknown_on_nonplayer_page(self):
        self.assertEqual(assess('<html>consent</html>')['status'],'unknown')
    def test_audit_unknown_on_restricted_player(self):
        self.assertEqual(assess('var ytInitialPlayerResponse = '+json.dumps({'playabilityStatus':{'status':'LOGIN_REQUIRED'}}))['status'],'unknown')
    def test_audit_present_and_absent(self):
        p={'playabilityStatus':{'status':'OK'},'captions':{'playerCaptionsTracklistRenderer':{'captionTracks':[{'languageCode':'zh','kind':'asr'}]}}}
        self.assertEqual(assess('var ytInitialPlayerResponse = '+json.dumps(p))['status'],'present')
        self.assertEqual(assess('var ytInitialPlayerResponse = '+json.dumps({'playabilityStatus':{'status':'OK'}}))['status'],'absent')
    def test_vtt_parser_short_timestamps_and_entities(self):
        p=self.d/'x.vtt'; p.write_text('WEBVTT\n\n00:00.000 --> 00:10.000 align:start\n你好 &amp; 世界\n')
        self.assertEqual(read_cues(p),[(0.,10.,'你好 & 世界')])
    def test_qc_uses_end_not_start(self):
        self.data(); r=self.run_script('qc.py','--dir',self.d); self.assertEqual(r.returncode,0,r.stdout+r.stderr)
        self.assertEqual(json.loads((self.d/'qc-report.json').read_text())['files'][0]['end_alignment_ratio'],1.)
    def test_empty_qc_fails(self): self.assertNotEqual(self.run_script('qc.py','--dir',self.d).returncode,0)
    def test_qc_missing_metadata_fails(self):
        (self.d/'x.zh.srt').write_text('1\n00:00:00,000 --> 00:00:05,000\n这是字幕\n')
        self.assertNotEqual(self.run_script('qc.py','--dir',self.d).returncode,0)
    def test_qc_repetition_fails(self):
        self.data(); p=next(self.d.glob('*.srt'))
        p.write_text('\n\n'.join(f'{i+1}\n00:00:0{i},000 --> 00:00:0{i+1},000\n这是重复句子。' for i in range(4)))
        result=self.run_script('qc.py','--dir',self.d); self.assertNotEqual(result.returncode,0)
        self.assertIn('repeated consecutive',result.stdout)
    def test_qc_numeric_run_fails(self):
        self.data(); p=next(self.d.glob('*.srt'))
        p.write_text('\n\n'.join(f'{i+1}\n00:00:0{i},000 --> 00:00:0{i+1},000\n{2020+i}' for i in range(6)))
        result=self.run_script('qc.py','--dir',self.d); self.assertNotEqual(result.returncode,0)
        self.assertIn('mostly numeric',result.stdout)
    def test_cleaner_preserves_existing_markdown(self):
        self.data(); out=self.d/'out'; r=self.run_script('clean_subs.py','--dir',self.d,'--out',out,'--subtitle-source','manual')
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)
        p=next(out.glob('*.md')); self.assertIn('subtitle_source: manual',p.read_text())
        p.write_text(p.read_text()+'\nUSER EDIT\n'); before=p.read_bytes()
        self.assertEqual(self.run_script('clean_subs.py','--dir',self.d,'--out',out).returncode,0)
        self.assertEqual(before,p.read_bytes())
    def test_index_good(self):
        out=self.notes(); r=self.run_script('validate_index.py','--out',out); self.assertEqual(r.returncode,0,r.stdout+r.stderr)
    def test_index_mixed_dead_legacy_reference_fails(self):
        out=self.notes(); p=next(out.glob('*总纲*')); p.write_text(p.read_text()+'\n[260101]\n')
        self.assertNotEqual(self.run_script('validate_index.py','--out',out).returncode,0)
    def test_date_mismatch_fails(self):
        out=self.notes(); p=next((out/'逐期').glob('*.md')); p.write_text(p.read_text().replace('date: "2026-10-05"','date: "2026-10-06"'))
        self.assertNotEqual(self.run_script('validate_index.py','--out',out).returncode,0)
    def test_invalid_method_timestamp_fails(self):
        out=self.notes(); p=next((out/'逐期').glob('*.md')); p.write_text(p.read_text().replace('。 [00:00:05]','。 [00:00:09]'))
        self.assertNotEqual(self.run_script('validate_index.py','--out',out).returncode,0)
    def test_same_day_citations_need_id(self):
        out=self.notes(); p=next((out/'逐期').glob('*.md')); q=p.with_name('20261005 - second [dEmO0000002].md'); q.write_text(p.read_text().replace('dEmO0000001','dEmO0000002'))
        syn=next(out.glob('*总纲*')); syn.write_text('# 总纲\n[20261005]\n')
        self.assertNotEqual(self.run_script('validate_index.py','--out',out).returncode,0)
        syn.write_text('# 总纲\n[video:dEmO0000001]\n[video:dEmO0000002]\n')
        self.assertEqual(self.run_script('validate_index.py','--out',out).returncode,0)
    def test_nonidempotent_cascade_never_writes(self):
        p=self.d/'x.srt'; p.write_text('A'); original=p.read_bytes()
        terms=self.d/'terms.json'; terms.write_text(json.dumps({'name':{'B':'C','A':'B'}}))
        result=self.run_script('fix_terms.py','--dir',self.d,'--terms',terms,'--check-idempotent')
        self.assertNotEqual(result.returncode,0)
        self.assertEqual(original,p.read_bytes())
    def test_timestamp_carry(self): self.assertEqual(ts(59.9996),'00:01:00,000')
if __name__=='__main__': unittest.main(verbosity=2)
