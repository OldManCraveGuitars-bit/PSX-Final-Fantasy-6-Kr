"""Create release-only archives; never includes ROM, BIOS, memory cards or states."""
from pathlib import Path
import argparse
import hashlib
import json
import zipfile

ROOT=Path(__file__).resolve().parents[1]


def digest(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def make_zip(name, files, text_files):
    output=ROOT/'release-assets'/(name+'.zip')
    output.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for path,relative in sorted(files,key=lambda item:item[1]):
            archive.write(path,name+'/'+relative)
        for relative,text in text_files.items():
            archive.writestr(name+'/'+relative,text.encode('utf-8'))
    return output


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--editor-exe',type=Path,required=True)
    args=parser.parse_args()
    common=[]
    for folder in ('licenses','docs'):
        common.extend((p,p.relative_to(ROOT).as_posix()) for p in (ROOT/folder).rglob('*') if p.is_file())
    for name in ('README.md','CHANGELOG.md','NOTICE.md','문장관리기-사용법.txt'):
        common.append((ROOT/name,name))
    url='https://github.com/OldManCraveGuitars-bit/PSX-Final-Fantasy-6-Kr'
    patcher_readme=('파이널 판타지 VI PSX 한글 패치 V0.75\n\n'
        '1. FF6-KR-Patcher-V0.75.exe 실행.\n2. 일본판 SLPM-86198 원본 BIN 선택.\n'
        '3. 저장할 폴더를 선택하고 한글 패치 적용.\n'
        '4. 새 FF6-KR-V0.75 폴더의 Final Fantasy VI (Korean V0.75).cue 실행.\n\n'
        '원본은 보존되며 이미 존재하는 출력 폴더를 덮어쓰지 않습니다.\n'
        '구버전 상태 저장 대신 새 CUE로 시작해 게임 내 저장을 불러오세요.\n'
        '원본 크기: 325,133,424 bytes\n'
        '원본 SHA-256: a607011d9c9442797ae155228e86e9dae6e503aaeb7dc9603ac552ffd8d036df\n'
        '결과 SHA-256: 6bb23a184380ce6c158185d4c634b4b0ca23a3196f16da47be2b40afd33b9454\n\n'
        '공개 V0.75의 내부 기준은 v084입니다. 오페라 가사 자막과 전체 플레이 검수는 미완료입니다.\n'
        '상세 설명: docs/INSTALL.md, README.md, docs/KNOWN_ISSUES.md\n'+url+'\n')
    exe=ROOT/'dist/FF6-KR-Patcher-V0.75.exe'
    assert exe.is_file() and args.editor_exe.is_file()
    manifest=json.loads((ROOT/'patcher/resources/manifest.json').read_text('utf8'))
    checked=json.loads((ROOT/'docs/verification/patcher-integration.json').read_text('utf8'))
    assert digest(exe)==checked['exe_sha256']
    packages=[]
    packages.append(make_zip('FF6-KR-Patcher-V0.75',common+[(exe,exe.name)],{'읽어주세요.txt':patcher_readme}))
    portable=list(common)
    for name in ('manifest.json','FF6-KR-V0.75.xdelta','xdelta3.exe'):
        portable.append((ROOT/'patcher/resources'/name,name))
    cue='FILE "'+manifest['target']['name']+'" BINARY\r\n  TRACK 01 MODE2/2352\r\n    INDEX 01 00:00:00\r\n'
    packages.append(make_zip('FF6-KR-V0.75-xdelta',portable,{
        'Final Fantasy VI (Korean V0.75).cue':cue,
        '읽어주세요.txt':'수동 xdelta 적용용 패키지입니다.\n\ndocs/INSTALL.md의 수동 적용 절차를 따르세요.\n원본 BIN과 BIOS는 포함되어 있지 않습니다.\n'+url+'\n'}))
    editor=list(common)+[(args.editor_exe,'FF6KoreanTextManager.exe'),(ROOT/'project-settings.json','project-settings.json')]
    for folder in ('translations','analysis','assets/text-manager'):
        editor.extend((p,p.relative_to(ROOT).as_posix()) for p in (ROOT/folder).rglob('*') if p.is_file() and p.suffix!='.pyc')
    packages.append(make_zip('FF6-Korean-Text-Manager-V1.13-V0.75',editor,{'읽어주세요.txt':
        'FF6 한글 문장 관리기 v1.13 / V0.75 편집 데이터\n\n'
        '압축 전체를 푼 뒤 FF6KoreanTextManager.exe를 실행하세요.\n'
        '프로젝트 선택창이 나오면 이 폴더를 선택하세요.\n'
        '7,720개 항목과 배치 설정을 제공합니다. 자세한 사용법은 docs/TEXT_MANAGER.md입니다.\n'
        '번역 JSON을 저장하는 도구이며 게임 BIN에 자동 삽입하지는 않습니다.\n'
        '갤러리의 원본 그림 위 미리보기에는 별도 로컬 추출 이미지가 필요합니다.\n'+url+'\n'}))
    hashes=''.join(digest(p)+'  '+p.name+'\n' for p in packages)
    (ROOT/'release-assets/SHA256SUMS.txt').write_text(hashes,'ascii')
    summary={'version':'V0.75','development_base':'v084','packages':[
        {'name':p.name,'bytes':p.stat().st_size,'sha256':digest(p)} for p in packages]}
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
