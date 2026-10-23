"""FF6 PSX Korean V0.76: verified, non-destructive xdelta patch application."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import queue
import shutil
import subprocess
import sys
import tempfile
import threading

VERSION = 'V0.76'


class PatchError(Exception):
    pass


def resource_root() -> Path:
    return Path(getattr(sys, '_MEIPASS', Path(__file__).parent)) / 'resources'


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def load_manifest() -> dict:
    m = json.loads((resource_root() / 'manifest.json').read_text('utf-8'))
    if m['version'] != VERSION or m['schema'] != 1:
        raise PatchError('지원하지 않는 패치 정보입니다.')
    for key in ('patch', 'decoder', 'target'):
        name = m[key]['name']
        if Path(name).name != name or '/' in name or '\\' in name:
            raise PatchError('패치 파일 정보가 잘못되었습니다.')
    return m


def check_resources(log=lambda _: None) -> dict:
    m = load_manifest()
    for key in ('patch', 'decoder'):
        item = m[key]
        path = resource_root() / item['name']
        if not path.is_file() or path.stat().st_size != item['size'] or sha256(path) != item['sha256']:
            raise PatchError('패처 내부 파일이 손상되었습니다. 공식 릴리스에서 다시 받으세요: ' + item['name'])
    log('패치 데이터와 변환 도구 무결성 확인 완료.')
    return m


def apply_patch(source: Path, parent: Path, log=lambda _: None) -> dict:
    source = source.expanduser().resolve(strict=True)
    parent = parent.expanduser().resolve(strict=True)
    if not source.is_file() or not parent.is_dir():
        raise PatchError('원본 BIN 파일과 저장할 폴더를 선택하세요.')
    m = check_resources(log)
    target = parent / 'FF6-KR-V0.76'
    if target.exists():
        raise PatchError('저장 폴더 안에 FF6-KR-V0.76 폴더가 이미 있습니다. 다른 저장 폴더를 선택하세요. 기존 파일은 덮어쓰지 않습니다.')
    log('원본 BIN 크기 확인 중…')
    expected = m['source']
    actual_size = source.stat().st_size
    if actual_size != expected['size']:
        raise PatchError(f"지원하는 일본판 원본 BIN은 {expected['size']:,}바이트입니다.\n선택한 파일: {actual_size:,}바이트. CUE·CHD·압축 파일이나 이미 패치한 BIN에는 적용할 수 없습니다.")
    log('원본 BIN SHA-256 검사 중…')
    actual_hash = sha256(source)
    if actual_hash != expected['sha256']:
        raise PatchError('원본이 일치하지 않습니다. 일본판 SLPM-86198의 지원되는 원본 덤프가 필요합니다.\n기대 SHA-256: ' + expected['sha256'] + '\n선택 SHA-256: ' + actual_hash)
    if shutil.disk_usage(parent).free < m['target']['size'] + 64 * 1024 * 1024:
        raise PatchError('저장 폴더에 최소 400 MB 정도의 여유 공간이 필요합니다.')
    log('원본 확인 완료. 한글 패치 적용 중…')
    # Only a newly created private temporary directory is removed on failure.
    # The source, existing destination, and the selected parent are never deleted.
    with tempfile.TemporaryDirectory(prefix='.ff6-kr-', dir=parent) as temporary:
        result_dir = Path(temporary) / 'result'
        result_dir.mkdir()
        output = result_dir / m['target']['name']
        command = [str(resource_root() / m['decoder']['name']), '-d', '-s', str(source),
                   str(resource_root() / m['patch']['name']), str(output)]
        done = subprocess.run(command, capture_output=True, encoding='utf-8', errors='replace',
                              creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        if done.returncode:
            raise PatchError('패치 변환에 실패했습니다. 원본은 변경되지 않았습니다.\n' + (done.stderr or done.stdout)[-1600:])
        log('완성된 BIN SHA-256 검사 중…')
        if output.stat().st_size != m['target']['size'] or sha256(output) != m['target']['sha256']:
            raise PatchError('완성 파일 검증에 실패했습니다. 결과 파일을 배포하지 않았습니다.')
        cue_name = output.with_suffix('.cue').name
        cue = f'FILE "{output.name}" BINARY\n  TRACK 01 MODE2/2352\n    INDEX 01 00:00:00\n'
        (result_dir / cue_name).write_text(cue, encoding='ascii', newline='\r\n')
        result = {'status': 'passed', 'version': VERSION, 'development_base': m['development_base'],
                  'source_sha256': actual_hash, 'target_sha256': m['target']['sha256'],
                  'target_size': m['target']['size'], 'cue': cue_name}
        (result_dir / 'patch-result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', 'utf-8')
        (result_dir / '읽어주세요.txt').write_text(
            '파이널 판타지 VI PSX 한글 패치 V0.76\n\n'
            + cue_name + ' 파일을 에뮬레이터에서 새로 실행하세요.\n'
            '이전 버전의 에뮬레이터 상태 저장은 사용하지 말고, 게임 내 메모리 카드 저장을 불러오세요.\n'
            '파일명이 바뀌면 에뮬레이터의 메모리 카드 연결을 확인하세요. 기존 카드는 먼저 백업하세요.\n'
            '공개 테스트 버전이며, 미완료 항목과 자세한 사용법은 공식 저장소를 확인하세요.\n'
            'https://github.com/OldManCraveGuitars-bit/PSX-Final-Fantasy-6-Kr\n', 'utf-8')
        # Windows refuses renaming onto an existing directory, including a racing run.
        # An extra existence check also covers ordinary use on other platforms.
        if target.exists():
            raise PatchError('다른 패치 작업이 같은 저장 폴더를 만들었습니다. 기존 결과는 보존했습니다.')
        os.rename(result_dir, target)
    log('완료: ' + str(target / cue_name))
    return {**result, 'output_directory': str(target)}


def launch_gui():
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except (AttributeError, OSError):
        pass
    root = tk.Tk()
    root.title('파이널 판타지 VI · PSX 한글 패처 ' + VERSION)
    root.geometry('740x570')
    root.minsize(650, 510)
    root.option_add('*Font', ('맑은 고딕', 10))
    frame = ttk.Frame(root, padding=24)
    frame.pack(fill='both', expand=True)
    ttk.Label(frame, text='FINAL FANTASY VI', font=('맑은 고딕', 20, 'bold')).pack(anchor='w')
    ttk.Label(frame, text='PlayStation 일본판 한글 패치  |  V0.76', font=('맑은 고딕', 12)).pack(anchor='w', pady=(4, 16))
    ttk.Label(frame, text='지원 원본: SLPM-86198 · BIN 325,133,424바이트\n원본은 보존하고 새 BIN/CUE를 만듭니다. Python 설치는 필요 없습니다.').pack(anchor='w')
    src, dest = tk.StringVar(), tk.StringVar()
    widgets = []
    for label, variable, is_source in [('1. 원본 일본판 BIN', src, True), ('2. 완성 파일을 저장할 폴더', dest, False)]:
        ttk.Label(frame, text=label).pack(anchor='w', pady=(16, 5))
        row = ttk.Frame(frame)
        row.pack(fill='x')
        entry = ttk.Entry(row, textvariable=variable)
        entry.pack(side='left', fill='x', expand=True, padx=(0, 8))
        def browse(var=variable, source=is_source):
            value = filedialog.askopenfilename(parent=root, title='원본 일본판 BIN 선택', filetypes=[('BIN 이미지', '*.bin'), ('모든 파일', '*.*')]) if source else filedialog.askdirectory(parent=root, title='결과를 저장할 폴더 선택')
            if value:
                var.set(value)
        button = ttk.Button(row, text='찾아보기', command=browse)
        button.pack(side='right')
        widgets.extend([entry, button])
    ttk.Label(frame, text='선택한 폴더 안에 FF6-KR-V0.76 폴더가 생성됩니다. 기존 결과는 덮어쓰지 않습니다.', wraplength=650).pack(anchor='w', pady=(8, 12))
    events = queue.Queue()
    busy = False
    progress = ttk.Progressbar(frame, mode='indeterminate')
    progress.pack(fill='x', pady=(0, 8))
    logbox = tk.Text(frame, height=7, wrap='word', state='disabled', font=('맑은 고딕', 9))
    logbox.pack(fill='both', expand=True)
    def append(message):
        logbox.configure(state='normal')
        logbox.insert('end', message + '\n')
        logbox.see('end')
        logbox.configure(state='disabled')
    def worker(source, destination):
        try:
            result = apply_patch(Path(source), Path(destination), lambda msg: events.put(('log', msg)))
            events.put(('success', result))
        except Exception as exc:
            events.put(('error', str(exc)))
    def start():
        nonlocal busy
        if not src.get().strip() or not dest.get().strip():
            messagebox.showerror('파일 선택', '원본 BIN과 저장할 폴더를 모두 선택하세요.', parent=root)
            return
        busy = True
        for widget in widgets:
            widget.configure(state='disabled')
        progress.start(12)
        threading.Thread(target=worker, args=(src.get().strip(), dest.get().strip()), daemon=True).start()
    apply_button = ttk.Button(frame, text='한글 패치 적용', command=start)
    apply_button.pack(fill='x', pady=(14, 0), ipady=6)
    widgets.append(apply_button)
    def poll():
        nonlocal busy
        try:
            while True:
                kind, value = events.get_nowait()
                if kind == 'log':
                    append(value)
                else:
                    busy = False
                    progress.stop()
                    for widget in widgets:
                        widget.configure(state='normal')
                    if kind == 'success':
                        messagebox.showinfo('패치 완료', 'BIN/CUE 생성과 해시 검사가 끝났습니다.\n\n' + value['output_directory'] + '\n\n이 폴더의 CUE를 새로 실행하세요.', parent=root)
                    else:
                        append('오류: ' + value)
                        messagebox.showerror('패치하지 못했습니다', value, parent=root)
        except queue.Empty:
            pass
        root.after(100, poll)
    def close():
        if busy:
            messagebox.showinfo('패치 진행 중', '파일 검증과 변환이 끝난 뒤 창을 닫아 주세요.', parent=root)
        else:
            root.destroy()
    root.protocol('WM_DELETE_WINDOW', close)
    append('원본 검사 → 패치 적용 → 결과 검사 순서로 진행합니다.')
    poll()
    root.mainloop()


def main():
    parser = argparse.ArgumentParser(description='FF6 PSX Korean V0.76 patcher')
    parser.add_argument('--source', type=Path)
    parser.add_argument('--output', type=Path, help='Existing parent folder for new FF6-KR-V0.76 folder')
    parser.add_argument('--self-check', action='store_true')
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    if not (args.self_check or args.source or args.output):
        launch_gui()
        return 0
    try:
        if args.self_check:
            manifest = check_resources()
            result = {'status': 'passed', 'version': VERSION, 'patch_sha256': manifest['patch']['sha256']}
        elif args.source and args.output:
            result = apply_patch(args.source, args.output, lambda line: print(line) if sys.stdout else None)
        else:
            raise PatchError('--source와 --output을 함께 지정하세요.')
        code = 0
    except Exception as exc:
        result, code = {'status': 'failed', 'error': str(exc)}, 1
    payload = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
    if args.report:
        args.report.write_text(payload, 'utf-8')
    if sys.stdout:
        print(payload)
    return code


if __name__ == '__main__':
    raise SystemExit(main())
