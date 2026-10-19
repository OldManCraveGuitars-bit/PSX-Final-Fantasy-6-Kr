"""Integration checks against the actual distributed Windows EXE.

Usage: python patcher/test_patcher.py --source ORIGINAL.bin --exe dist/PATCHER.exe
Requires a user-owned original; all generated images stay in an owned tempdir.
"""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--exe',type=Path,required=True)
    parser.add_argument('--report',type=Path,required=True)
    args=parser.parse_args()
    source,exe=args.source.resolve(),args.exe.resolve()
    m=json.loads((Path(__file__).parent/'resources/manifest.json').read_text('utf8'))
    assert digest(source)==m['source']['sha256']
    results={}
    with tempfile.TemporaryDirectory(prefix='FF6 한글 패처 검증 ') as temporary:
        root=Path(temporary)
        def run(label,expected,*params):
            report=root/(label+'.json')
            process=subprocess.run([str(exe),*map(str,params),'--report',str(report)],timeout=180)
            result=json.loads(report.read_text('utf8'))
            assert process.returncode==expected,(label,process.returncode,result)
            assert result['status']==('passed' if expected==0 else 'failed')
            results[label]=True
            return result
        run('embedded_resources',0,'--self-check')
        out=run('packaged_exe_roundtrip',0,'--source',source,'--output',root)
        dest=Path(out['output_directory'])
        image=dest/m['target']['name']
        assert image.stat().st_size==m['target']['size']
        assert digest(image)==m['target']['sha256']
        cue=(dest/Path(m['target']['name']).with_suffix('.cue')).read_text('ascii')
        assert 'FILE "'+image.name+'" BINARY' in cue and 'TRACK 01 MODE2/2352' in cue
        results['cue_matches_verified_bin']=True
        marker=dest/'existing-marker.txt';marker.write_text('preserve me','utf8')
        run('existing_destination_rejected',1,'--source',source,'--output',root)
        assert marker.read_text('utf8')=='preserve me' and digest(image)==m['target']['sha256']
        next_parent=root/'다른 출력 폴더';next_parent.mkdir()
        wrong=root/'wrong.bin';wrong.write_bytes(b'not a game')
        run('wrong_size_rejected',1,'--source',wrong,'--output',next_parent)
        shutil.copyfile(source,wrong)
        with wrong.open('r+b') as stream:
            first=stream.read(1);stream.seek(0);stream.write(bytes([first[0]^1]))
        run('same_size_wrong_hash_rejected',1,'--source',wrong,'--output',next_parent)
        run('already_patched_image_rejected',1,'--source',image,'--output',next_parent)
        assert not any(next_parent.iterdir())
        results['failed_runs_leave_no_output']=True
        assert digest(source)==m['source']['sha256']
        results['original_source_unchanged']=True
        results['unicode_and_space_output_path']=True
    payload={'version':m['version'],'development_base':m['development_base'],
             'source_sha256':m['source']['sha256'],'target_sha256':m['target']['sha256'],
             'exe_sha256':digest(exe),'checks':results}
    args.report.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n','utf8')
    print(json.dumps(payload,ensure_ascii=True,indent=2))


if __name__=='__main__':main()
