"""FF6 Korean text manager: a self-contained Windows desktop editor."""
from __future__ import annotations
import argparse
import ctypes
from dataclasses import asdict, replace
import json
import os
from pathlib import Path
import re
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageDraw, ImageFont, ImageTk
from text_manager_model import Store, Metrics, Profile, CONTROL, TOKEN, audit, write_report, monster_popup_profile

VERSION = '1.14'
RESOURCE = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent.parent/'assets/text-manager'))
FONTS = {'large': '큰 글씨 12px', 'battle':'전투 큰 글씨 고정 12px', 'small': '작은 글씨 갈무리7 / 8px', 'bonus': '부록 큰 글씨 12×12', 'psx': 'PSX 메시지 12×12', 'subtitle': '자막 12×12'}
PRESETS = {
    '대사 기본: 216px / 4줄': Profile(),
    '프롤로그: 가운데 / 216px': Profile(center=True),
    '전투: 고정 12px / 216px': Profile('battle',216,4,16,True,note='전투 큰 글씨는 영문·숫자·문장부호도 고정 12px. 동적 변수와 화면별 높이는 별도 확인.'),
    '몬스터 메시지: 한 줄씩 전환 / 216px': monster_popup_profile(),
    '도구 설명: 216px / 2줄': Profile(width=216, rows=2, auto_wrap=False, note='도구 목록 위 설명 영역의 검사값. 문장이 여러 출력 경로에서 쓰이면 각각 검사하세요.'),
    '환수 요약: 120px / 1줄': Profile(width=120, rows=1, auto_wrap=False,confirmed=True,note='실제 환수 목록·특수 화면의 한 줄 요약. 보수적 폭 120px.'),
    '부록 몬스터: 216px / 6줄': Profile('bonus', 216, 6, 12, True, confirmed=True, note='빌드 시 검증되는 부록 몬스터 설명 한계.'),
    '직업: 작은 글씨 / 80px': Profile('small', 80, 1, 8, False, note='메인 메뉴 직업란의 보수적 검사 영역.'),
    '메뉴 헤더: 작은 글씨 / 40px': Profile('small', 40, 1, 8, False, note='메뉴 헤더의 보수적 검사 영역. 이웃 항목 간격도 확인하세요.'),
    '자막: 12×12 / 304px / 2줄': Profile('subtitle', 304, 2, 14, False, center=True, confirmed=True, note='OPEN/OPERA/END 별도 자막. 각 줄 304px, 최대 두 줄.'),
}


def resource(name):
    return RESOURCE/name


class Editor:
    def __init__(self, window, root):
        self.window = window
        self.store = Store(root)
        self.metrics = Metrics(json.loads(resource('text-metrics.json').read_text('utf-8')))
        self.current = None
        self.pending = {}
        self.busy = False
        self.preview_job = None
        self.filter_job = None
        self.images = []
        self.cache = {}
        self.issues_by_uid = {}
        self.search = tk.StringVar()
        self.group = tk.StringVar(value='전체 분류')
        self.status_filter = tk.StringVar(value='전체 상태')
        self.reviewed = tk.BooleanVar()
        self.font = tk.StringVar(value=FONTS['large'])
        self.width = tk.IntVar(value=216)
        self.rows = tk.IntVar(value=4)
        self.pitch = tk.IntVar(value=16)
        self.autowrap = tk.BooleanVar(value=True)
        self.center = tk.BooleanVar()
        self.confirmed = tk.BooleanVar()
        self.grid = tk.BooleanVar(value=True)
        self.spaces = tk.BooleanVar(value=True)
        self.zoom = tk.StringVar(value='3')
        self.preset = tk.StringVar(value=next(iter(PRESETS)))
        self.stats = tk.StringVar()
        self.notice = tk.StringVar(value='대사·메뉴·설명·전투 문장을 한곳에서 관리합니다. Ctrl+S 저장 / Ctrl+F 검색.')
        window.title(f'FF6 한글 문장 관리기 {VERSION} — {self.store.root.name}')
        window.geometry('1380x940'); window.minsize(1080, 760)
        window.protocol('WM_DELETE_WINDOW', self.close)
        self.build_ui()
        self.fill_list()
        window.bind('<Control-s>', lambda e: self.save_current())
        window.bind('<Control-Shift-S>', lambda e: self.save_all())
        window.bind('<Control-f>', lambda e: self.search_box.focus_set())
        window.bind('<F5>', lambda e: self.check_all())
        if self.store.records:
            self.tree.selection_set(self.store.records[0].uid)
            self.select_record()

    def build_ui(self):
        style = ttk.Style(); style.theme_use('clam')
        style.configure('.', font=('맑은 고딕', 10))
        style.configure('Treeview', rowheight=25)
        style.configure('Title.TLabel', font=('맑은 고딕', 13, 'bold'))
        toolbar = ttk.Frame(self.window, padding=(12, 8)); toolbar.pack(fill='x')
        ttk.Label(toolbar, text='FF6 한글 문장 관리기', style='Title.TLabel').pack(side='left', padx=(0, 18))
        for label, command in [('프로젝트 열기', self.open_project), ('현재 저장', self.save_current), ('수정분 모두 저장', self.save_all), ('전체 검사 F5', self.check_all), ('검사표 내보내기', self.export)]:
            ttk.Button(toolbar, text=label, command=command).pack(side='left', padx=3)
        ttk.Button(toolbar, text='일괄 가져오기', command=self.import_batch).pack(side='left', padx=3)
        ttk.Button(toolbar, text='자막 등록', command=self.import_subtitles).pack(side='left', padx=3)
        ttk.Button(toolbar, text='도움말', command=self.help).pack(side='right')
        ttk.Label(self.window, text=str(self.store.root), padding=(14, 0, 0, 7), foreground='#596779').pack(anchor='w')
        panes = ttk.Panedwindow(self.window, orient='horizontal'); panes.pack(fill='both', expand=True, padx=10)
        left = ttk.Frame(panes); right = ttk.Frame(panes)
        panes.add(left, weight=1); panes.add(right, weight=3)
        self.search_box = ttk.Entry(left, textvariable=self.search)
        self.search_box.pack(fill='x', pady=(0, 5))
        ttk.Label(left, text='원문·번역 검색 / #번호로 ID 검색', foreground='#657386').pack(anchor='w')
        filters = ttk.Frame(left); filters.pack(fill='x', pady=6)
        self.group_box=ttk.Combobox(filters, textvariable=self.group, values=['전체 분류']+list(dict.fromkeys(r.group for r in self.store.records)), state='readonly', width=16)
        self.group_box.pack(side='left', fill='x', expand=True)
        ttk.Combobox(filters, textvariable=self.status_filter, values=['전체 상태', '초안', '검수 완료', '검사 문제'], state='readonly', width=11).pack(side='left', padx=(4, 0))
        listframe = ttk.Frame(left); listframe.pack(fill='both', expand=True)
        self.tree = ttk.Treeview(listframe, columns=('id', 'state', 'text'), show='headings', selectmode='browse')
        for col, title, width in [('id', '분류 / ID', 120), ('state', '상태', 55), ('text', '번역', 200)]:
            self.tree.heading(col, text=title); self.tree.column(col, width=width, minwidth=40, stretch=col=='text')
        scroll = ttk.Scrollbar(listframe, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side='left', fill='both', expand=True); scroll.pack(side='right', fill='y')
        self.tree.tag_configure('draft', foreground='#8a5b13')
        self.tree.tag_configure('error', foreground='#c62828')
        self.tree.tag_configure('pending', background='#fff1bd')
        self.tree.bind('<<TreeviewSelect>>', lambda e: self.select_record())
        ttk.Label(left, textvariable=self.stats, padding=(0, 5)).pack(anchor='w')
        self.notebook = ttk.Notebook(right); self.notebook.pack(fill='both', expand=True)
        edit = ttk.Frame(self.notebook, padding=8); report = ttk.Frame(self.notebook, padding=8)
        self.notebook.add(edit, text='문장 편집 · 칸 검사'); self.notebook.add(report, text='전체 검사 결과')
        self.identity = ttk.Label(edit, text='', style='Title.TLabel'); self.identity.pack(anchor='w')
        self.location = ttk.Label(edit, text='', foreground='#667788'); self.location.pack(anchor='w', pady=(2, 5))
        textpanes = ttk.Panedwindow(edit, orient='horizontal'); textpanes.pack(fill='x')
        source_frame = ttk.LabelFrame(textpanes, text='원문', padding=4)
        ko_frame = ttk.LabelFrame(textpanes, text='한글 번역 (제어 코드는 그대로 보존)', padding=4)
        textpanes.add(source_frame, weight=1); textpanes.add(ko_frame, weight=1)
        self.source = tk.Text(source_frame, height=8, wrap='word', font=('맑은 고딕', 11), background='#f0f3f7', relief='flat')
        self.source.pack(fill='both', expand=True)
        self.translation = tk.Text(ko_frame, height=8, wrap='word', font=('맑은 고딕', 11), undo=True, relief='flat')
        self.translation.pack(fill='both', expand=True)
        self.translation.bind('<<Modified>>', self.modified)
        actions = ttk.Frame(edit); actions.pack(fill='x', pady=6)
        ttk.Checkbutton(actions, text='검수 완료', variable=self.reviewed, command=self.changed).pack(side='left')
        ttk.Button(actions, text='반각 공백으로 정리', command=self.normalize_spaces).pack(side='left', padx=5)
        ttk.Button(actions, text='줄바꿈을 편집문에 적용', command=self.apply_wrap).pack(side='left')
        ttk.Button(actions, text='현재 내용 되돌리기', command=self.revert).pack(side='right')
        settings = ttk.LabelFrame(edit, text='검사 영역 — 글꼴 크기는 게임 출력 크기 유지', padding=6); settings.pack(fill='x')
        presets = ttk.Frame(settings); presets.pack(fill='x', pady=(0, 5))
        ttk.Label(presets, text='화면 기준').pack(side='left', padx=(0, 6))
        ttk.Combobox(presets, textvariable=self.preset, values=list(PRESETS), state='readonly', width=34).pack(side='left')
        ttk.Button(presets, text='검사 영역 적용', command=self.apply_preset).pack(side='left', padx=6)
        row1 = ttk.Frame(settings); row1.pack(fill='x')
        ttk.Combobox(row1, textvariable=self.font, values=list(FONTS.values()), state='readonly', width=23).pack(side='left')
        for title, variable, lo, hi in [('폭 px', self.width, 8, 640), ('줄 수', self.rows, 1, 40), ('줄 간격 px', self.pitch, 8, 48)]:
            ttk.Label(row1, text=title).pack(side='left', padx=(9, 3))
            ttk.Spinbox(row1, textvariable=variable, from_=lo, to=hi, width=5, command=self.changed).pack(side='left')
        row2 = ttk.Frame(settings); row2.pack(fill='x', pady=(5, 0))
        for title, variable in [('삽입 시 자동 줄바꿈', self.autowrap), ('가운데 정렬', self.center), ('실제 칸 경계 확인 완료', self.confirmed)]:
            ttk.Checkbutton(row2, text=title, variable=variable, command=self.changed).pack(side='left', padx=(0, 10))
        self.profile_note = ttk.Label(settings, text='', foreground='#667788', wraplength=780)
        self.profile_note.pack(anchor='w', pady=(5, 0))
        previewbar = ttk.Frame(edit); previewbar.pack(fill='x', pady=5)
        self.measure = ttk.Label(previewbar, text=''); self.measure.pack(side='left')
        ttk.Combobox(previewbar, textvariable=self.zoom, values=['1', '2', '3', '4'], state='readonly', width=3).pack(side='right')
        ttk.Label(previewbar, text='배율').pack(side='right', padx=(5, 2))
        ttk.Checkbutton(previewbar, text='공백 표시', variable=self.spaces, command=self.refresh_preview).pack(side='right')
        ttk.Checkbutton(previewbar, text='격자', variable=self.grid, command=self.refresh_preview).pack(side='right', padx=5)
        canvasframe = ttk.Frame(edit); canvasframe.pack(fill='both', expand=True)
        self.canvas = tk.Canvas(canvasframe, background='#dbe1eb', highlightthickness=0, height=235)
        vscroll = ttk.Scrollbar(canvasframe, orient='vertical', command=self.canvas.yview)
        hscroll = ttk.Scrollbar(canvasframe, orient='horizontal', command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=vscroll.set, xscrollcommand=hscroll.set)
        self.canvas.grid(row=0, column=0, sticky='nsew'); vscroll.grid(row=0, column=1, sticky='ns'); hscroll.grid(row=1, column=0, sticky='ew')
        canvasframe.rowconfigure(0, weight=1); canvasframe.columnconfigure(0, weight=1)
        self.issue_box = tk.Text(edit, height=5, wrap='word', font=('맑은 고딕', 10), background='#f7f8fb', relief='flat')
        self.issue_box.pack(fill='x', pady=(6, 0))
        self.issue_box.tag_configure('오류', foreground='#b71c1c'); self.issue_box.tag_configure('주의', foreground='#a65a00'); self.issue_box.tag_configure('참고', foreground='#596779')
        ttk.Label(report, text='오류 행을 두 번 누르면 해당 문장으로 이동합니다. 검사에는 저장 전 수정분도 포함됩니다.').pack(anchor='w', pady=(0, 8))
        self.report_tree = ttk.Treeview(report, columns=('group', 'id', 'severity', 'bounds', 'message'), show='headings')
        for col, title, width in [('group', '분류', 110), ('id', 'ID', 50), ('severity', '구분', 50), ('bounds', '칸 경계', 65), ('message', '검사 내용', 435)]:
            self.report_tree.heading(col, text=title); self.report_tree.column(col, width=width, stretch=col=='message')
        self.report_tree.pack(side='left', fill='both', expand=True)
        sb = ttk.Scrollbar(report, command=self.report_tree.yview); sb.pack(side='right', fill='y'); self.report_tree.configure(yscrollcommand=sb.set)
        self.report_tree.bind('<Double-1>', self.report_select)
        self.report_links = {}
        ttk.Label(self.window, textvariable=self.notice, padding=(12, 7), anchor='w').pack(fill='x')
        for variable in (self.search, self.group, self.status_filter):
            variable.trace_add('write', lambda *a: self.queue_filter())
        for variable in (self.font, self.width, self.rows, self.pitch):
            variable.trace_add('write', lambda *a: self.changed())
        self.zoom.trace_add('write', lambda *a: self.refresh_preview())

    def text(self):
        return self.translation.get('1.0', 'end-1c')

    def profile(self):
        font = next(k for k, v in FONTS.items() if v == self.font.get())
        width, rows, pitch = self.width.get(), self.rows.get(), self.pitch.get()
        if not (8 <= width <= 640 and 1 <= rows <= 40 and 8 <= pitch <= 48):
            raise ValueError('폭 8~640px, 줄 수 1~40, 줄 간격 8~48px 범위로 입력하세요.')
        return replace(self.current.profile if self.current else Profile(),font=font,width=width,rows=rows,pitch=pitch,
            auto_wrap=self.autowrap.get(),center=self.center.get(),confirmed=self.confirmed.get(),
            note=self.profile_note.cget('text') if self.current else '')

    def capture(self):
        if not self.current or self.busy:
            return
        profile = self.profile()
        value = (self.text(), self.reviewed.get(), profile)
        original = (self.current.text, self.current.reviewed, self.current.profile)
        if value != original:
            self.pending[self.current.uid] = value
        else:
            self.pending.pop(self.current.uid, None)
        self.update_row(self.current)

    def modified(self, event=None):
        if self.translation.edit_modified():
            self.translation.edit_modified(False); self.changed()

    def changed(self, *args):
        if self.busy:
            return
        if self.preview_job:
            self.window.after_cancel(self.preview_job)
        self.preview_job = self.window.after(170, self.refresh_preview)

    def update_row(self, r):
        if not self.tree.exists(r.uid):
            return
        text, reviewed, _ = self.pending.get(r.uid, (r.text, r.reviewed, r.profile))
        errors = any(i.severity=='오류' for i in self.issues_by_uid.get(r.uid, []))
        tags = (['draft'] if not reviewed else []) + (['error'] if errors else []) + (['pending'] if r.uid in self.pending else [])
        self.tree.item(r.uid, values=(f'{r.group} / {r.key}', ('*' if r.uid in self.pending else '')+('완료' if reviewed else '초안'), CONTROL.sub('◇', text).replace('\n', ' / ')[:95]), tags=tags)

    def queue_filter(self):
        if self.filter_job:
            self.window.after_cancel(self.filter_job)
        self.filter_job = self.window.after(250, self.fill_list)

    def fill_list(self):
        self.filter_job = None
        try:
            self.capture()
        except (ValueError, tk.TclError):
            return
        query = self.search.get().casefold().strip(); group = self.group.get(); status = self.status_filter.get()
        current = self.current.uid if self.current else None
        self.busy = True
        self.tree.delete(*self.tree.get_children())
        visible = 0
        for r in self.store.records:
            text, reviewed, _ = self.pending.get(r.uid, (r.text, r.reviewed, r.profile))
            if group != '전체 분류' and group != r.group: continue
            if status == '초안' and reviewed: continue
            if status == '검수 완료' and not reviewed: continue
            if status == '검사 문제' and not any(i.severity!='참고' for i in self.issues_by_uid.get(r.uid, [])): continue
            if query:
                if query.startswith('#'):
                    if query[1:] != r.key.casefold(): continue
                elif query not in (r.source+'\n'+text+'\n'+r.key).casefold(): continue
            self.tree.insert('', 'end', iid=r.uid); self.update_row(r); visible += 1
        if current and self.tree.exists(current):
            self.tree.selection_set(current)
        self.busy = False
        reviewed = sum(self.pending.get(r.uid, (r.text, r.reviewed, r.profile))[1] for r in self.store.records)
        self.stats.set(f'{visible:,} / {len(self.store.records):,}항목 · 검수 {reviewed:,} · 수정 {len(self.pending)}')

    def select_record(self):
        if self.busy or not self.tree.selection(): return
        uid = self.tree.selection()[0]
        if self.current and self.current.uid == uid: return
        try:
            self.capture()
        except (ValueError, tk.TclError) as e:
            messagebox.showerror('검사 영역 확인', str(e)); return
        r = self.store.by_uid[uid]; self.current = r
        text, reviewed, profile = self.pending.get(uid, (r.text, r.reviewed, r.profile))
        self.busy = True
        self.source.configure(state='normal'); self.source.delete('1.0', 'end'); self.source.insert('1.0', r.source or '(원문 정보 없음)'); self.source.configure(state='disabled')
        self.source_image=None
        if r.group=='갤러리 설명':
            path=self.store.root/'analysis/gallery-assets'/f"{Path(r.meta['file']).stem}-{r.meta['image']:02}.png"
            if path.exists():
                boxes=[r.meta['rect']]+r.meta.get('erase_rects',[])
                x=min(b[0] for b in boxes);y=min(b[1] for b in boxes)
                w=max(b[0]+b[2] for b in boxes)-x;h=max(b[1]+b[3] for b in boxes)-y
                im=Image.open(path).convert('RGB').crop((x,y,x+w,y+h))
                self.source_image=ImageTk.PhotoImage(im.resize((w*2,h*2),Image.Resampling.NEAREST))
                self.source.configure(state='normal');self.source.insert('end','\n\n');self.source.image_create('end',image=self.source_image);self.source.configure(state='disabled')
        self.translation.delete('1.0', 'end'); self.translation.insert('1.0', text); self.translation.edit_reset(); self.translation.edit_modified(False)
        self.reviewed.set(reviewed); self.font.set(FONTS[profile.font]); self.width.set(profile.width); self.rows.set(profile.rows); self.pitch.set(profile.pitch)
        self.autowrap.set(profile.auto_wrap); self.center.set(profile.center); self.confirmed.set(profile.confirmed)
        self.identity.configure(text=f'{r.group} · ID {r.key}'+(f' · {r.category}' if r.category else ''))
        self.location.configure(text=r.file+(' · 저장 시 검수본/초안으로 분리' if r.kind=='main' else ''))
        if r.group=='동영상 자막':
            self.location.configure(text=f"{r.meta.get('movie','OPERA')} · {r.meta['start_frame']}~{r.meta['end_frame']}프레임 · {r.meta['start_frame']/15:.2f}~{r.meta['end_frame']/15:.2f}초 (15fps)")
        if r.group=='갤러리 설명':self.location.configure(text=f"{r.meta['file']} · 그림 {r.meta['image']+1} · 영역 {r.meta['rect']}")
        self.profile_note.configure(text=profile.note)
        self.busy = False; self.refresh_preview()

    def glyph(self, token, profile):
        key = (token, profile.font)
        if key in self.cache: return self.cache[key]
        size = 8 if profile.font=='small' else 12
        im = Image.new('RGBA', (size, size))
        original = self.metrics.data.get('original_bitmaps', {}).get(token)
        if profile.font in ('large','battle') and original:
            for y, row in enumerate(original):
                for x in range(12):
                    if row & (1 << (11-x)): im.putpixel((x, y), (255, 255, 255, 255))
        else:
            fontfile = 'Galmuri7.ttf' if size==8 else 'Galmuri9.ttf'
            ft = ImageFont.truetype(str(resource(fontfile)), 8 if size==8 else 10)
            ImageDraw.Draw(im).text((0, 0) if size==8 else (1, -1), token, font=ft, fill='white')
        self.cache[key] = im
        return im

    def refresh_preview(self, *args):
        self.preview_job = None
        if self.busy or not self.current: return
        try:
            self.capture(); profile = self.profile()
            self.metrics.refresh_variables(self.store.records, {uid: value[0] for uid, value in self.pending.items()})
            issues, effective, lines = self.metrics.check(self.current, self.text(), profile)
        except (ValueError, tk.TclError) as e:
            self.notice.set(str(e)); return
        self.issues_by_uid[self.current.uid] = issues
        self.issue_box.configure(state='normal'); self.issue_box.delete('1.0', 'end')
        if not issues:
            self.issue_box.insert('end', '정해진 검사 영역 안에 들어갑니다.\n')
        for i in issues:
            self.issue_box.insert('end', f'[{i.severity}] {i.message}\n', i.severity)
        self.issue_box.configure(state='disabled')
        pages = sorted({line.page for line in lines}); scale = int(self.zoom.get())
        widest = max((line.width for line in lines), default=0)
        self.measure.configure(text=f'최대 {widest}/{profile.width}px · {len(pages)}쪽 · 글자 {profile.cell}px / 공백 {profile.space}px')
        self.canvas.delete('all'); self.images = []
        y = 10; totalwidth = max(profile.width+widest-profile.width, profile.width)*scale+110
        for page in pages:
            page_lines = [line for line in lines if line.page==page]
            height = max(profile.rows, len(page_lines))*profile.pitch
            self.canvas.create_text(12, y, anchor='nw', text=f'{page}쪽', fill='#344459', font=('맑은 고딕', 10, 'bold'))
            y += 23
            x0 = 28; y0 = y
            gallery_white=self.current.group=='갤러리 설명' and self.current.meta.get('background','white')=='white'
            gallery_black=self.current.group=='갤러리 설명' and not gallery_white
            self.canvas.create_rectangle(x0-3, y0-3, x0+profile.width*scale+3, y0+profile.rows*profile.pitch*scale+3, fill='white' if gallery_white else ('black' if gallery_black else '#151f60'), outline='#8290bd', width=2)
            if self.grid.get():
                for x in range(0, profile.width+1, profile.cell):
                    self.canvas.create_line(x0+x*scale, y0, x0+x*scale, y0+profile.rows*profile.pitch*scale, fill='#2d397b')
                for row in range(profile.rows+1):
                    self.canvas.create_line(x0, y0+row*profile.pitch*scale, x0+profile.width*scale, y0+row*profile.pitch*scale, fill='#2d397b')
            self.canvas.create_line(x0+profile.width*scale, y0, x0+profile.width*scale, y0+height*scale, fill='#ff5555', dash=(4, 3), width=2)
            for line in page_lines:
                x = line.offset; ly = y0+(line.number-1+(max(0,profile.rows-len(page_lines)) if profile.font=='subtitle' else 0))*profile.pitch*scale
                if line.number>profile.rows:
                    self.canvas.create_rectangle(x0, ly, x0+max(widest, profile.width)*scale, ly+profile.pitch*scale, fill='#5a293f', outline='')
                for token in line.tokens:
                    n = self.metrics.advance(token, profile)
                    if token==' ':
                        if self.spaces.get(): self.canvas.create_oval(x0+(x+max(1,n//2))*scale, ly+(profile.cell-2)*scale, x0+(x+max(1,n//2))*scale+2, ly+(profile.cell-2)*scale+2, fill='#7cc8ef', outline='')
                    elif token.startswith('{'):
                        if token=='{key}' and profile.font=='battle':
                            # Native wait keeps X. Mark the wait at the cursor
                            # without reserving a cell or creating a new page.
                            self.canvas.create_line(x0+x*scale,ly-2,x0+x*scale,ly+profile.cell*scale,fill='#f2c766',dash=(2,2),tags='battle_key_wait')
                        elif n:
                            self.canvas.create_rectangle(x0+x*scale, ly, x0+(x+n)*scale-1, ly+profile.cell*scale-1, outline='#ddbb59')
                            if n>=30: self.canvas.create_text(x0+(x+n/2)*scale, ly+profile.cell*scale/2, text='이름/변수' if 'char' in token else token[1:-1], fill='#edcf76', font=('맑은 고딕', 8))
                    else:
                        glyph = self.glyph(token, profile).copy()
                        if gallery_white:
                            dark=Image.new('RGBA',glyph.size,(0,0,0,0));dark.putalpha(glyph.getchannel('A'));glyph=dark
                        glyph=glyph.resize((profile.cell*scale, profile.cell*scale),Image.Resampling.NEAREST)
                        image = ImageTk.PhotoImage(glyph); self.images.append(image)
                        self.canvas.create_image(x0+x*scale, ly, image=image, anchor='nw')
                    x += n
                self.canvas.create_text(x0+max(profile.width, widest)*scale+10, ly, anchor='nw', text=f'{line.width}px', fill='#bb2525' if line.width>profile.width else '#46556a', font=('맑은 고딕', 9))
            y += height*scale+24
        self.canvas.configure(scrollregion=(0, 0, max(totalwidth, self.canvas.winfo_width()), y))
        self.update_row(self.current)
        self.notice.set(f'수정 {len(self.pending)}항목 · 반각 공백: 큰 글씨 6px / 작은 글씨 4px · 변수는 최대 6글자 이름 폭으로 검사합니다.')

    def normalize_spaces(self):
        text = self.text().replace('\r', '')
        text = ''.join(' ' if c.isspace() and c!='\n' else c for c in text)
        self.translation.delete('1.0', 'end'); self.translation.insert('1.0', text); self.changed()

    def apply_wrap(self):
        if not self.current: return
        try:
            text = self.metrics.check(self.current,self.text(),replace(self.profile(),auto_wrap=True))[1]
            self.translation.delete('1.0', 'end'); self.translation.insert('1.0', text); self.changed()
        except (ValueError, tk.TclError) as e:
            messagebox.showerror('줄바꿈', str(e))

    def apply_preset(self):
        if not self.current: return
        profile = PRESETS[self.preset.get()]
        self.busy = True
        self.font.set(FONTS[profile.font]); self.width.set(profile.width); self.rows.set(profile.rows); self.pitch.set(profile.pitch)
        self.autowrap.set(profile.auto_wrap); self.center.set(profile.center); self.confirmed.set(profile.confirmed)
        self.profile_note.configure(text=profile.note)
        self.busy = False; self.changed()

    def revert(self):
        if not self.current: return
        uid = self.current.uid; self.pending.pop(uid, None); self.current = None; self.tree.selection_set(uid); self.select_record()

    def save_current(self):
        if not self.current: return
        try:
            self.capture(); uid = self.current.uid
            if uid not in self.pending:
                self.notice.set('현재 항목에 저장할 변경 사항이 없습니다.'); return
            backup = self.store.save(self.current, *self.pending[uid], self.metrics)
            self.pending.pop(uid)
            self.busy=True; self.translation.delete('1.0', 'end'); self.translation.insert('1.0', self.current.text); self.translation.edit_modified(False); self.busy=False
            self.update_row(self.current); self.refresh_preview()
            self.notice.set(f'저장했습니다. 자동 백업: {backup.name}')
        except Exception as e:
            messagebox.showerror('저장하지 못했습니다', str(e))

    def save_all(self):
        try:
            self.capture(); count = len(self.pending)
            if not count:
                self.notice.set('저장할 수정 항목이 없습니다.'); return
            items=[(self.store.by_uid[uid],*value) for uid,value in self.pending.items()]
            self.store.save_many(items,self.metrics)
            self.pending.clear()
            if self.current:
                self.busy=True; self.translation.delete('1.0', 'end'); self.translation.insert('1.0', self.current.text); self.translation.edit_modified(False); self.busy=False
            self.fill_list(); self.refresh_preview(); self.notice.set(f'{count}개 수정 항목을 함께 저장했습니다. 저장 전 원본을 자동 백업했습니다.')
        except Exception as e:
            messagebox.showerror('일부 항목을 저장하지 못했습니다', str(e))

    def import_batch(self):
        path=filedialog.askopenfilename(title='번역 항목 JSON 가져오기',filetypes=[('문장 관리기 JSON','*.json')],initialdir=self.store.root/'work')
        if not path:return
        try:
            self.capture()
            items=self.store.import_items(json.loads(Path(path).read_text('utf-8')))
            # Validate all structural constraints before touching even the open
            # edit buffers. Canonical files are written only with Save All.
            temporary={}
            for r,text,reviewed,profile in items:
                self.store.plan_save(r,text,reviewed,profile,self.metrics,temporary)
            for r,text,reviewed,profile in items:self.pending[r.uid]=(text,reviewed,profile)
            current=self.current.uid if self.current else None
            self.current=None;self.fill_list()
            if current and self.tree.exists(current):self.tree.selection_set(current);self.select_record()
            self.notice.set(f'{len(items)}개 항목을 불러왔습니다. 확인 후 수정분 모두 저장을 누르세요.')
        except Exception as e:messagebox.showerror('가져오지 못했습니다',str(e))

    def import_subtitles(self):
        if not self.finish_pending():return
        path=filedialog.askopenfilename(title='전체 자막 목록 등록 (OPEN/OPERA/END, 프레임 포함 JSON)',
            initialdir=self.store.root/'work',filetypes=[('JSON 자막 목록','*.json')])
        if not path:return
        try:
            backup=self.store.import_subtitles(json.loads(Path(path).read_text('utf8')),self.metrics)
            self.group_box.configure(values=['전체 분류']+list(dict.fromkeys(r.group for r in self.store.records)))
            self.current=None;self.issues_by_uid={};self.group.set('전체 분류');self.search.set('');self.fill_list()
            self.notice.set(f'자막 목록을 등록했습니다. 자동 백업: {backup.name}')
        except Exception as e:messagebox.showerror('자막을 등록하지 못했습니다',str(e))

    def results(self):
        self.capture(); temporary = []
        for uid, (text, reviewed, profile) in self.pending.items():
            r = self.store.by_uid[uid]; temporary.append((r, r.text, r.reviewed, r.profile)); r.text = text; r.reviewed = reviewed; r.profile = profile
        try:
            return audit(self.store, self.metrics)
        finally:
            for r, text, reviewed, profile in temporary:
                r.text = text; r.reviewed = reviewed; r.profile = profile

    def check_all(self):
        try:
            results = self.results()
        except Exception as e:
            messagebox.showerror('검사', str(e)); return
        self.report_tree.delete(*self.report_tree.get_children()); self.report_links = {}
        count = 0; errors = 0
        for row in results:
            self.issues_by_uid[row['uid']] = self.metrics.check(self.store.by_uid[row['uid']], self.pending.get(row['uid'], (row['translation'],))[0], Profile(**row['profile']))[0]
            for issue in row['issues']:
                if issue['severity']=='참고': continue
                iid = str(count); self.report_links[iid] = row['uid']; count += 1
                if issue['severity']=='오류': errors += 1
                self.report_tree.insert('', 'end', iid=iid, values=(row['group'], row['id'], issue['severity'], '확인' if row['profile']['confirmed'] else '추정', issue['message']))
        self.notebook.select(1)
        self.notice.set(f'{len(results):,}항목 검사 완료 · 오류 {errors:,} / 주의 {count-errors:,}. 화면 경계 미확정 항목은 별도 표시됩니다.')

    def report_select(self, event=None):
        selection = self.report_tree.selection()
        if not selection: return
        uid = self.report_links[selection[0]]
        self.search.set(''); self.group.set('전체 분류'); self.status_filter.set('전체 상태'); self.fill_list()
        self.tree.selection_set(uid); self.tree.see(uid); self.select_record(); self.notebook.select(0)

    def export(self):
        path = filedialog.asksaveasfilename(title='검사 결과 저장', initialdir=self.store.root/'analysis', initialfile='text-manager-check.csv', defaultextension='.csv', filetypes=[('CSV 검사표', '*.csv'), ('JSON 상세 검사표', '*.json')])
        if not path: return
        try:
            write_report(path, self.results()); self.notice.set('검사표를 저장했습니다: '+str(path))
        except Exception as e:
            messagebox.showerror('내보내기', str(e))

    def open_project(self):
        path = filedialog.askdirectory(title='FF6 한글화 프로젝트 폴더', initialdir=self.store.root)
        if not path: return
        if not self.finish_pending(): return
        try:
            store = Store(path)
        except Exception as e:
            messagebox.showerror('프로젝트', str(e)); return
        self.store = store; self.current = None; self.pending = {}; self.issues_by_uid = {}
        self.group.set('전체 분류'); self.search.set(''); self.status_filter.set('전체 상태'); self.fill_list()
        self.window.title(f'FF6 한글 문장 관리기 {VERSION} — {store.root.name}')
        if store.records: self.tree.selection_set(store.records[0].uid); self.select_record()

    def finish_pending(self):
        try:
            self.capture()
        except (ValueError, tk.TclError) as e:
            messagebox.showerror('검사 영역', str(e)); return False
        if not self.pending: return True
        answer = messagebox.askyesnocancel('저장 전 수정분', f'{len(self.pending)}개 수정분을 저장할까요?\n아니오를 누르면 저장 전 수정분을 버립니다.')
        if answer is None: return False
        if answer:
            self.save_all(); return not self.pending
        return True

    def close(self):
        if self.finish_pending(): self.window.destroy()

    def help(self):
        messagebox.showinfo('사용 방법',
            '1. 분류와 검색으로 문장을 고르고 한글 번역을 수정합니다.\n'
            '2. 실제 글자 크기와 반각 공백으로 칸 넘침·줄 수·줄 간격을 검사합니다.\n'
            '3. 화면별 폭·줄 수를 입력하고 경계 확인을 체크해 저장할 수 있습니다.\n'
            '4. Ctrl+S: 현재 저장 / Ctrl+Shift+S: 수정분 모두 저장 / F5: 전체 검사.\n\n'
            '노란 행은 저장 전 수정분입니다. 제어 코드·서식 변수·전각 공백 오류는 저장을 막습니다. '
            '칸 넘침은 초안에서도 확인할 수 있도록 저장을 허용합니다.\n\n'
            '자동 줄바꿈을 켜고 저장하면 검사 폭에 맞춘 줄바꿈을 번역 파일에도 저장합니다. '
            '글꼴·줄 간격 설정은 검사할 출력 경로를 선택하는 값이며 게임의 글꼴 크기 자체를 바꾸지 않습니다.\n\n'
            '전투 {key}는 줄을 바꾸지 않는 입력 대기입니다. 앞뒤 문장의 폭을 합쳐 검사하며 미리보기의 노란 점선으로 표시합니다.\n'
            '자동 백업: work/text-manager-backups. 외부 수정과 충돌하면 덮어쓰지 않습니다.\n'
            '갤러리 설명은 원본 글자 영역 이미지를 함께 보여 줍니다. 그림별 고정 영역 밖으로 넘치는 번역은 저장하지 않습니다.\n'
            '메인 대사는 검수본/초안, 부록은 원본 번역 파일에 연결됩니다. 저장 후 ROM을 다시 빌드해야 게임에 반영됩니다.\n\n'
            '확인된 폭: 대사 216px, 부록 설명 216px/6줄, 자막 각 줄 304px/최대 2줄. '
            '나머지 화면은 기본 참고 영역이므로 실제 칸 크기를 저장하세요. '
            '영문·아이콘은 출력 경로에 따라 모양이 다를 수 있습니다. '
            '미리보기는 텍스트 영역 검사이며 VRAM·그래픽 안전성은 게임 실행 검사가 필요합니다.')


def find_project(given=None):
    if given: return Path(given)
    roots = [Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parents[1], Path.cwd()]
    for root in roots:
        if (root/'project-settings.json').exists(): return root
    return None


def run_widget_test(project, report_path):
    """Exercise our own Tk widgets without driving any other desktop app."""
    project = Path(project)
    if not (project/'.editor-test-only').exists():
        raise ValueError('Widget regression saves require an isolated .editor-test-only project.')
    window = tk.Tk(); window.withdraw()
    callback_errors = []
    window.report_callback_exception = lambda *args: callback_errors.append(str(args))
    app = Editor(window, project)
    window.update_idletasks(); window.update()
    assert any(i.code=='font_path' for i in app.metrics.check(app.current, profile=replace(app.current.profile, font='small'))[0])
    uid = next(r.uid for r in app.store.records if r.group=='대사' and r.key=='6')
    app.group.set('대사'); app.search.set('#6'); app.fill_list()
    assert list(app.tree.get_children()) == [uid]
    app.tree.selection_set(uid); app.select_record(); window.update()
    assert app.center.get() and len(app.canvas.find_all()) > 20
    app.autowrap.set(False); app.width.set(48); app.confirmed.set(True); app.refresh_preview()
    assert any(i.code=='width' for i in app.issues_by_uid[uid])
    # Restore the prologue settings; test persistence on an ordinary text row.
    app.revert(); app.group.set('전체 분류'); app.search.set(''); app.fill_list()
    uid = next(r.uid for r in app.store.records if r.group=='대사' and r.key=='1000')
    app.tree.selection_set(uid); app.select_record()
    original = app.current.text
    app.width.set(120); app.autowrap.set(True)
    app.translation.insert('end', ' 검사 문장입니다.'); app.refresh_preview()
    assert uid in app.pending
    app.save_current()
    assert uid not in app.pending
    reloaded = Store(project).by_uid[uid]
    assert reloaded.text == app.metrics.wrap(original+' 검사 문장입니다.', app.current.profile)
    assert reloaded.profile.width == 120
    assert list((project/'work/text-manager-backups').glob('*/manifest.json'))
    app.check_all(); window.update()
    assert app.report_tree.get_children()
    assert app.notebook.index(app.notebook.select()) == 1
    caption=next((r for r in app.store.records if r.group=='동영상 자막' and r.meta.get('movie')=='OPEN'),None)
    if caption:
        app.group.set('동영상 자막');app.search.set('#'+caption.key);app.fill_list()
        app.tree.selection_set(caption.uid);app.select_record();app.refresh_preview();window.update()
        assert app.center.get() and (app.current.profile.rows,app.current.profile.pitch)==(2,14)
        assert 'OPEN' in app.location.cget('text') and '프레임' in app.location.cget('text')
        assert not any(i.severity=='오류' for i in app.issues_by_uid[caption.uid])
    gallery=next((r for r in app.store.records if r.group=='갤러리 설명' and r.key=='G2-12-metal'),None)
    if gallery:
        app.group.set('갤러리 설명');app.search.set('#'+gallery.key);app.fill_list()
        app.tree.selection_set(gallery.uid);app.select_record();app.refresh_preview();window.update()
        assert app.source_image is not None
        assert app.current.profile.font=='small' and app.current.profile.width==gallery.meta['rect'][2]
        assert any(app.canvas.type(v)=='rectangle' and app.canvas.itemcget(v,'fill')=='white' for v in app.canvas.find_all())
        assert not any(i.severity=='오류' for i in app.issues_by_uid[gallery.uid])
    monster=next((r for r in app.store.records if r.category=='monster_dialogue' and r.meta.get('index')==139),None)
    if monster:
        app.group.set(monster.group);app.search.set('#'+monster.key);app.fill_list()
        app.tree.selection_set(monster.uid);app.select_record();app.refresh_preview();window.update()
        assert app.current.profile.newline_pages and app.rows.get()==1 and not app.autowrap.get()
        assert '7쪽' in app.measure.cget('text')
        assert not any(i.severity=='오류' for i in app.issues_by_uid[monster.uid])
        app.autowrap.set(True);app.refresh_preview()
        assert any(i.code=='popup_wrap' for i in app.issues_by_uid[monster.uid])
        app.autowrap.set(False);app.refresh_preview();app.save_current()
        assert Store(project).by_uid[monster.uid].profile.newline_pages
    inline=next((r for r in app.store.records if r.category=='battle_dialogue' and r.meta.get('index')==6),None)
    if inline:
        app.group.set(inline.group);app.search.set('#'+inline.key);app.fill_list()
        app.tree.selection_set(inline.uid);app.select_record();app.refresh_preview();window.update()
        _,lines=app.metrics.layout(inline.text,app.current.profile)
        assert len({line.page for line in lines})==1 and lines[-1].width==156
        assert len(app.canvas.find_withtag('battle_key_wait'))==3
        assert not any(i.severity=='오류' for i in app.issues_by_uid[inline.uid])
        # A future edit crossing the same inline wait must show real overflow.
        app.translation.delete('1.0','end')
        app.translation.insert('1.0','가'*10+'{key}'+'나'*9)
        app.autowrap.set(False);app.refresh_preview();window.update()
        assert any(i.code=='width' for i in app.issues_by_uid[inline.uid])
        app.revert()
    assert not callback_errors, callback_errors
    result = {'entries': len(app.store.records), 'search_and_ID_filter': True,
              'native_font_canvas_rendered': True, 'centered_prologue_preview': True,
              'width_overflow_visible': True, 'save_and_reopen': True,
              'large_font_path_guard': True,
              'custom_wrap_persisted': True, 'layout_settings_persisted': True,
              'timed_caption_preview':bool(caption),
              'gallery_original_crop_and_fixed_bounds_preview':bool(gallery),
              'native_monster_sequential_preview_and_timing_guard':bool(monster),
              'battle_inline_key_width_and_wait_markers':bool(inline),
              'automatic_backup': True, 'all_record_check_tab': True,
              'Tk_callback_errors': callback_errors}
    Path(report_path).write_text(json.dumps(result, ensure_ascii=False, indent=2), 'utf-8')
    window.destroy()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--project')
    parser.add_argument('--audit', metavar='REPORT', help='No GUI: write JSON/CSV layout report and exit.')
    parser.add_argument('--self-check', metavar='REPORT', help='No GUI: validate packaged fonts, metrics and project loading.')
    parser.add_argument('--smoke-test', metavar='REPORT', help='Run the editor widget regression test in an isolated project.')
    parser.add_argument('--apply-batch', metavar='JSON', help='Validate, back up and atomically import a reviewed text batch.')
    parser.add_argument('--import-subtitles', metavar='JSON', help='Validate and register a complete OPEN/OPERA/END timed cue list.')
    parser.add_argument('--import-bonus-small', metavar='JSON', help='Register newly discovered bonus labels and catalog references.')
    parser.add_argument('--import-gallery', metavar='JSON', help='Validate and register gallery text rectangles.')
    parser.add_argument('--import-boost', metavar='JSON', help='Validate and register the native boost-page labels.')
    parser.add_argument('--report', metavar='JSON', help='Write the batch-import audit report.')
    args = parser.parse_args()
    project = find_project(args.project)
    if args.import_bonus_small:
        if not project:raise ValueError('Use --project PROJECT_FOLDER')
        store=Store(project);metrics=Metrics(json.loads(resource('text-metrics.json').read_text('utf8')))
        backup=store.import_bonus_small(json.loads(Path(args.import_bonus_small).read_text('utf8')),metrics)
        target=Path(args.report) if args.report else store.root/'analysis/text-manager-bonus-small-import.json'
        target.write_text(json.dumps({'version':VERSION,'backup':str(backup),
            'records':[r for r in audit(store,metrics) if r['group']=='부록 작은 글씨']},ensure_ascii=False,indent=2)+'\n','utf8')
        return
    if args.import_boost:
        if not project:raise ValueError('Use --project PROJECT_FOLDER')
        store=Store(project);metrics=Metrics(json.loads(resource('text-metrics.json').read_text('utf8')))
        backup=store.import_boost(json.loads(Path(args.import_boost).read_text('utf8')),metrics)
        target=Path(args.report) if args.report else store.root/'analysis/text-manager-boost-import.json'
        target.write_text(json.dumps({'version':VERSION,'backup':str(backup),
            'records':[r for r in audit(store,metrics) if r['group']=='부스트 설정']},ensure_ascii=False,indent=2)+'\n','utf8')
        return
    if args.import_gallery:
        if not project:raise ValueError('Use --project PROJECT_FOLDER')
        store=Store(project);metrics=Metrics(json.loads(resource('text-metrics.json').read_text('utf-8')))
        backup=store.import_gallery(json.loads(Path(args.import_gallery).read_text('utf8')),metrics)
        target=Path(args.report) if args.report else store.root/'analysis/text-manager-gallery-import.json'
        target.write_text(json.dumps({'version':VERSION,'backup':str(backup),
            'records':[r for r in audit(store,metrics) if r['group']=='갤러리 설명']},ensure_ascii=False,indent=2)+'\n','utf8')
        return
    if args.import_subtitles:
        if not project:raise ValueError('Use --project PROJECT_FOLDER')
        store=Store(project);metrics=Metrics(json.loads(resource('text-metrics.json').read_text('utf-8')))
        backup=store.import_subtitles(json.loads(Path(args.import_subtitles).read_text('utf-8')),metrics)
        target=Path(args.report) if args.report else store.root/'analysis/text-manager-subtitle-import.json'
        target.write_text(json.dumps({'version':VERSION,'imported_records':sum(r.group=='동영상 자막' for r in store.records),
            'backup':str(backup),'records':[r for r in audit(store,metrics) if r['group']=='동영상 자막']},ensure_ascii=False,indent=2)+'\n','utf-8')
        return
    if args.apply_batch:
        if not project:raise ValueError('Use --project PROJECT_FOLDER')
        store=Store(project);metrics=Metrics(json.loads(resource('text-metrics.json').read_text('utf-8')))
        items=store.import_items(json.loads(Path(args.apply_batch).read_text('utf-8')))
        metrics.refresh_variables(store.records,{r.uid:text for r,text,_,_ in items})
        backup=store.save_many(items,metrics)
        selected={r.uid for r,_,_,_ in items}
        report={'imported_records':len(items),'backup':str(backup),'records':[row for row in audit(store,metrics) if row['uid'] in selected]}
        target=Path(args.report) if args.report else store.root/'analysis/text-manager-last-import.json'
        target.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf-8')
        return
    if args.audit or args.self_check:
        if not project: raise ValueError('Use --project PROJECT_FOLDER')
        metrics = Metrics(json.loads(resource('text-metrics.json').read_text('utf-8')))
        store = Store(project)
        if args.audit:
            write_report(args.audit, audit(store, metrics))
        else:
            for filename, size in [('Galmuri7.ttf', 8), ('Galmuri9.ttf', 10)]:
                ImageFont.truetype(str(resource(filename)), size).getmask('한글')
            Path(args.self_check).write_text(json.dumps({'version': VERSION, 'entries': len(store.records), 'fonts': 'loaded', 'space_pixels': [6, 4], 'subtitle_cell': [12, 12]}, ensure_ascii=False, indent=2), 'utf-8')
        return
    if args.smoke_test:
        if not project: raise ValueError('Use --project PROJECT_FOLDER')
        run_widget_test(project, args.smoke_test)
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    window = tk.Tk()
    try:
        if not project:
            window.withdraw(); project = filedialog.askdirectory(title='FF6 한글화 프로젝트 폴더')
            if not project: window.destroy(); return
            window.deiconify()
        Editor(window, project)
        window.mainloop()
    except Exception as e:
        messagebox.showerror('FF6 문장 관리기', str(e)); window.destroy(); raise


if __name__ == '__main__':
    main()
