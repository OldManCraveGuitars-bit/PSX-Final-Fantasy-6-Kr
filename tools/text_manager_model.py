"""Standalone text-store and native-pixel layout engine for the FF6 editor.

Only the Python standard library is needed here. The GUI bundles Pillow/fonts.
Canonical translation files are edited; generated build output is never a source.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict, replace
from pathlib import Path
import csv
import hashlib
import io
import json
import os
import re
import shutil
import unicodedata
import uuid
from datetime import datetime
from caption_format import validate_caption_rows
from gallery_format import validate_gallery_rows
from psx_label_format import label_capacity, encoded_size
from boost_format import WIDTHS as BOOST_WIDTHS, validate_boost_rows

TOKEN = re.compile(r'\{[^{}]+\}|[^{}]')
CONTROL = re.compile(r'\{[^{}]+\}')
JP = re.compile(r'[\u3041-\u3096\u309d-\u309f\u30a1-\u30fa\u30fd-\u30ff\u3400-\u9fff\uff66-\uff9f]')
PRINTF = re.compile(r'%(?:[-+0 #]*\d*(?:\.\d+)?[diuxXsf]|[p])')


def load_json(path, default=None):
    return json.loads(path.read_text('utf-8')) if path.exists() else default


def normalized(text):
    return unicodedata.normalize('NFKC', text).replace('\r', '').replace('…', '…').replace('–', 'ー').replace('—', 'ー').replace('〜', '～')


@dataclass
class Profile:
    font: str = 'large'
    width: int = 216
    rows: int = 4
    pitch: int = 16
    auto_wrap: bool = True
    center: bool = False
    confirmed: bool = False
    note: str = '대사 폭 216px. 높이는 기본 4줄이며 스크롤 구간은 별도 확인.'
    numeric_pixels: int = 0
    newline_pages: bool = False

    @property
    def cell(self):
        return 8 if self.font == 'small' else 12

    @property
    def space(self):
        return self.cell // 2


def gallery_profile(row):
    _,_,w,h=row['rect']
    return Profile('small',w,max(1,h//10),10,True,center=row.get('center',False),
        confirmed=True,note='갤러리 원본 640×480의 지정 글자 영역. 갈무리7 / 글자 8px, 공백 4px. 그림·테두리는 보존합니다.')


def monster_popup_profile(profile=None):
    return replace(profile or Profile('battle',216,1,16,False), rows=1,
        auto_wrap=False, newline_pages=True, confirmed=True,
        note='몬스터 대사는 상단 한 줄씩 출력하고 줄바꿈 때 다음 화면으로 넘깁니다. 큰 글씨 12px / 공백 6px. 원래 {pause}·{wait} 코드를 유지하며 자동 줄바꿈은 사용하지 않습니다.')


@dataclass
class Record:
    uid: str
    group: str
    key: str
    source: str
    text: str
    reviewed: bool
    file: str
    kind: str = 'dict'
    category: str = ''
    profile: Profile | None = None
    baseline_controls: tuple = ()
    meta: dict | None = None
    baseline_printf: tuple = ()


@dataclass
class Issue:
    severity: str
    code: str
    message: str
    page: int = 0
    line: int = 0


@dataclass
class Line:
    tokens: list
    width: int
    page: int
    number: int
    offset: int = 0


class Metrics:
    def __init__(self, data=None):
        self.data = data or {}
        self.widths = self.data.get('widths', {})
        self.variable_pixels = dict(self.data.get('variable_pixels', {}))

    def refresh_variables(self, records, overrides=None):
        """Use the current edited catalog, including unsaved name changes."""
        overrides = overrides or {}
        maxima = {}
        for r in records:
            if r.group != '이름·도구·마법' or r.category not in ('item', 'spell', 'monster', 'attack', 'command','monster_attack','esper_attack'):
                continue
            text = CONTROL.sub('', normalized(overrides.get(r.uid, r.text)))
            width = sum(6 if c==' ' else self.widths.get(c, 12) for c in text)
            maxima[r.category] = max(maxima.get(r.category, 0), width)
            battle_width=sum(6 if c==' ' else 12 for c in text)
            maxima['battle_'+r.category]=max(maxima.get('battle_'+r.category,0),battle_width)
        self.variable_pixels.update(maxima)

    def advance(self, token, profile):
        if token == ' ':
            return profile.space
        if token.startswith('{'):
            # Legacy metrics also listed bytecode controls as menu icons.
            # Pauses/colors/end markers never occupy a glyph cell.
            if token in ('{pause}','{key}','{end}','{0}','{n}','{color}'):
                return 0
            if re.fullmatch(r'\{t\[[0-9a-fA-F]{2}\]\}', token):
                return int(token[3:5], 16) * profile.space
            if re.fullmatch(r'\{h?char(?:\d+|\[[0-9a-fA-F]{2}\])\}', token):
                return profile.cell * 6
            if token in ('{item}', '{spell}', '{gp}'):
                return int(self.variable_pixels.get(token[1:-1], 120))
            match = re.fullmatch(r'\{([a-z0-9_]+)\[[0-9a-fA-F]{2}\]\}', token)
            if match and match[1] in ('item', 'spell', 'monster', 'attack', 'command', 'monster_number', 'slot2', 'slot3', 'slot4', 'string'):
                if profile.font=='battle':
                    # Native battle string slots: actor, item, attack, command.
                    # The corresponding SNES engine is documented in
                    # src/btlgfx/menu.asm DlgTextCmd_12 and HexToDec24.
                    if match[1]=='string':
                        kind=int(token[token.index('[')+1:-2],16)
                        if kind==0:return 72
                        if kind==1:return int(self.variable_pixels.get('battle_item',120))
                        if kind==2:return max(int(self.variable_pixels.get('battle_'+c,120)) for c in ('spell','attack','monster_attack','esper_attack'))
                        if kind==3:return int(self.variable_pixels.get('battle_command',120))
                    elif match[1] in ('item','spell','monster','attack','command'):
                        return int(self.variable_pixels.get('battle_'+match[1],120))
                if match[1] == 'string': return profile.width
                return int(self.variable_pixels.get(match[1], 120))
            if re.fullmatch(r'\{var[0-3]\}', token):
                return (profile.numeric_pixels or 96) if profile.font=='battle' else 120
            if token in ('{choice}',):
                return 0
            if token in self.data.get('icons', []):
                return profile.cell
            return 0
        if profile.font in ('bonus', 'subtitle', 'psx', 'battle'):
            return 12
        return 8 if profile.font == 'small' else int(self.widths.get(token, 12))

    def wrap(self, text, profile, safe=False):
        """Native word-first breaks, with optional maximum variable reservation.

        Compatibility mode audits the existing ROM builder. Safe mode is used
        by the editor and persisted when saving a newly checked entry.
        """
        out, line, pixels = [], [], 0
        def advance(token):
            if not safe and token in ('{item}', '{spell}', '{gp}'): return 80
            return self.advance(token, profile)
        for token in TOKEN.findall(normalized(text)):
            if token == '\n' or token == '{page}' or (token == '{key}' and profile.font!='battle'):
                out.extend(line); line = []; pixels = 0; out.append(token)
                continue
            n = advance(token)
            if pixels + n > profile.width and line:
                if token == ' ':
                    out.extend(line); out.append('\n'); line = []; pixels = 0
                    continue
                spaces = [i for i, t in enumerate(line) if t == ' ']
                if spaces:
                    cut = spaces[-1]
                    out.extend(line[:cut]); out.append('\n')
                    line = line[cut + 1:]
                    pixels = sum(advance(t) for t in line)
                else:
                    out.extend(line); out.append('\n'); line = []; pixels = 0
                if pixels + n > profile.width and line:
                    out.extend(line); out.append('\n'); line = []; pixels = 0
            line.append(token); pixels += n
        out.extend(line)
        return ''.join(out)

    def layout(self, text, profile):
        effective = self.wrap(text, profile, safe=True) if profile.auto_wrap else normalized(text)
        lines, tokens, page, number = [], [], 1, 1
        def flush():
            nonlocal tokens, number
            width = sum(self.advance(t, profile) for t in tokens)
            offset = max(0, int(((profile.width-width)/2)/profile.space+0.5))*profile.space if profile.center else 0
            if profile.font=='subtitle' and profile.center:offset=max(0,(profile.width-width)//2)
            lines.append(Line(tokens, width, page, number, offset)); tokens = []; number += 1
        for token in TOKEN.findall(effective):
            if token == '\n':
                flush()
                if profile.newline_pages:
                    page += 1; number = 1
            elif token == '{page}' or (token == '{key}' and profile.font!='battle'):
                flush(); page += 1; number = 1
            elif profile.center and re.fullmatch(r'\{t\[[0-9A-Fa-f]{2}\]\}', token):
                continue
            else:
                tokens.append(token)
        if tokens or not lines:
            flush()
        return effective, lines

    def bonus_wrap(self, text, profile):
        # The insertion code reflows monster-description paragraphs as prose,
        # then wraps whole words. A long unbreakable word must remain visible
        # as an overflow, rather than silently passing a different algorithm.
        lines=[]
        for source in text.split('\n'):
            line=''
            for word in source.split(' '):
                candidate=(line+' '+word) if line else word
                if sum(self.advance(c,profile) for c in candidate)>profile.width and line:
                    lines.append(line);line=word
                else:line=candidate
            lines.append(line)
        return '\n'.join(lines)

    def check(self, record, text=None, profile=None):
        text = record.text if text is None else text
        profile = profile or record.profile or Profile()
        issues = []
        fonts = {
            '대사': ('large',), 'PSX 도움말': ('large',), '지역명': ('large',),
            '설명문': ('large',), '전투 문장': ('battle',), '전투 기술·대사': ('battle',),
            '메뉴 글씨': ('small',), '직업': ('small',), '부록 작은 글씨': ('small',),
            'PSX 작은 글씨': ('small',), '부록 문장': ('bonus',),
            'PSX 저장·불러오기': ('psx',), '동영상 자막': ('subtitle',),
            '갤러리 설명': ('small',),
            '부스트 설정': ('small',),
        }.get(record.group, ('large', 'small'))
        if profile.font not in fonts:
            issues.append(Issue('오류', 'font_path', '선택한 글꼴이 이 문장의 실제 출력 경로와 다릅니다. 원래 글꼴 크기로 검사하세요.'))
        monster_popup = record.category=='monster_dialogue'
        if record.group=='부스트 설정':
            limit=BOOST_WIDTHS[record.key]
            if profile.width>limit or profile.rows!=1 or profile.auto_wrap or '\n' in text or sum(4 if c==' ' else 8 for c in text)>limit:
                issues.append(Issue('오류','boost_bounds','부스트의 고정 칸 너비와 한 줄 배치를 유지하세요.'))
        if monster_popup:
            if not profile.newline_pages or profile.rows!=1 or profile.width>216:
                issues.append(Issue('오류','popup_flow','몬스터 메시지는 상단 216px 이내의 한 줄 전환 방식으로 검사하세요. 몬스터 메시지 프리셋을 선택하세요.'))
            if profile.auto_wrap:
                issues.append(Issue('오류','popup_wrap','몬스터 메시지의 자동 줄바꿈은 화면 전환 시간을 바꿉니다. 끄고 원래 대기 코드를 유지해 문장을 다듬으세요.'))
        elif profile.newline_pages:
            issues.append(Issue('오류','popup_flow','줄마다 다음 화면으로 넘기는 검사는 몬스터 메시지에서만 사용합니다.'))
        if record.group=='갤러리 설명':
            _,_,w,h=record.meta['rect']
            if profile.width>w or profile.rows*profile.pitch>h:
                issues.append(Issue('오류','gallery_bounds','검사 영역이 원본 그림의 지정 글자 영역보다 큽니다.'))
        if record.group=='이름·도구·마법' and record.category=='character':
            if len(normalized(text))>6 or '\n' in text:
                issues.append(Issue('오류','name_length','캐릭터 이름은 반각 공백을 포함해 최대 6글자, 한 줄입니다.'))
        if record.group=='PSX 작은 글씨' and record.source:
            capacity=label_capacity(record.source)
            if encoded_size(text)>capacity:
                issues.append(Issue('오류','psx_literal_capacity',f'고정 메뉴 문자열 저장 공간: {encoded_size(text)} / {capacity}바이트. 글꼴 크기를 유지하고 문구를 줄이세요.'))
        signature = tuple(CONTROL.findall(text))
        if signature != record.baseline_controls:
            issues.append(Issue('오류', 'controls', '제어 코드/아이콘/변수의 종류 또는 순서가 달라졌습니다.'))
        if '{' in CONTROL.sub('', text) or '}' in CONTROL.sub('', text):
            issues.append(Issue('오류', 'braces', '닫히지 않은 제어 코드 괄호가 있습니다.'))
        if tuple(PRINTF.findall(text)) != record.baseline_printf:
            issues.append(Issue('오류', 'printf', '숫자·문자열 서식 변수(%d 등)가 달라졌습니다.'))
        if PRINTF.findall(text):
            issues.append(Issue('주의', 'printf_width', '서식 변수(%d·%s 등)는 실행 중 값이 바뀝니다. 최장 실제 값의 폭도 확인하세요.'))
        if re.search(r'\{string\[', text):
            issues.append(Issue('주의', 'dynamic_string', '동적 문장 변수는 한 줄 폭을 예약했습니다. 실제 내용의 줄 수도 확인하세요.'))
        if JP.search(CONTROL.sub('', text)):
            issues.append(Issue('주의', 'japanese', '일본어 또는 한자가 남아 있습니다.'))
        if any(c.isspace() and c not in (' ', '\n', '\r') for c in text):
            issues.append(Issue('오류', 'space', '반각 공백(U+0020)이 아닌 공백 또는 탭이 있습니다.'))
        if re.search(r' {2,}', text):
            issues.append(Issue('주의', 'double_space', '연속 공백이 있습니다. 의도한 들여쓰기인지 확인하세요.'))
        if re.search(r' +\n| +$', text):
            issues.append(Issue('주의', 'trailing_space', '줄 끝에 공백이 있습니다.'))
        if any(unicodedata.combining(c) or '\u1100' <= c <= '\u11ff' for c in text):
            issues.append(Issue('오류', 'composition', '완성되지 않은 자모 또는 결합 문자가 있습니다.'))
        if any(ord(c) < 32 and c not in '\r\n\t' for c in text):
            issues.append(Issue('오류', 'control_character', '저장할 수 없는 제어 문자가 있습니다.'))
        if profile.pitch < profile.cell:
            issues.append(Issue('오류', 'pitch', f'줄 간격 {profile.pitch}px이 글자 높이 {profile.cell}px보다 작아 겹칩니다.'))
        if record.group=='부록 문장' and profile.auto_wrap:
            prose=normalized(text).replace('갓파','임프')
            if 89<=int(record.key)<=521:prose=' '.join(prose.split())
            effective=self.bonus_wrap(prose,profile)
            _,lines=self.layout(effective,replace(profile,auto_wrap=False))
        else:
            effective, lines = self.layout(text, profile)
        for line in lines:
            if line.offset + line.width > profile.width:
                issues.append(Issue('오류', 'width', f'{line.page}쪽 {line.number}줄: {line.width}px / {profile.width}px, {line.offset+line.width-profile.width}px 초과.', line.page, line.number))
        pages = {}
        for line in lines:
            pages[line.page] = pages.get(line.page, 0) + 1
        for page, count in pages.items():
            if count > profile.rows:
                issues.append(Issue('오류' if profile.confirmed else '주의', 'height', f'{page}쪽: {count}줄 / {profile.rows}줄. 칸 높이 또는 스크롤 여부를 확인하세요.', page))
        if not profile.confirmed:
            issues.append(Issue('참고', 'bounds', '화면별 칸 높이·폭은 추정값입니다. 실제 칸을 확인한 뒤 검사 영역을 저장하세요.'))
        # A conservative editorial hint, never an automatic rewrite.
        if record.group in ('대사', 'PSX 도움말', '설명문', '전투 문장', '전투 기술·대사', '부록 문장', 'PSX 저장·불러오기', '동영상 자막'):
            # Choices are labels, including any wrapped continuation lines.
            # Keep prose after a real page/message boundary in the check.
            prose = re.sub(r'\{choice\}.*?(?=\{(?:choice|page|key(?:\[[^]]+\])?)\}|$)', '', text, flags=re.S)
            plain = CONTROL.sub('', prose).rstrip(' \r\n」』”"\'♬♪♫')
            if plain not in ('예','아니요','아니오') and re.search(r'[가-힣](?:다|요|죠|렴|거라)$', plain):
                issues.append(Issue('주의', 'period', '문장 끝 마침표가 빠졌을 수 있습니다.'))
        if record.group == '동영상 자막':
            meta = record.meta or {}
            if profile.width>304 or profile.rows>2 or profile.pitch!=14:
                issues.append(Issue('오류','caption_layout','실제 자막은 각 줄 304px, 최대 2줄, 줄 간격 14px입니다.'))
            if not (0 <= meta.get('start_frame', -1) < meta.get('end_frame', -1) < 65536):
                issues.append(Issue('오류', 'timing', '자막 시작·끝 프레임을 확인하세요.'))
            if any(len(line)>43 for line in normalized(text).split('\n')):
                issues.append(Issue('오류', 'caption_length', '현재 자막 엔진의 한 줄 43자 제한을 넘었습니다.'))
        return issues, effective, lines


class ConflictError(RuntimeError):
    pass


class Store:
    def __init__(self, root):
        self.root = Path(root).resolve()
        if not (self.root/'project-settings.json').exists():
            raise ValueError('FF6 한글화 프로젝트 폴더를 선택하세요.')
        self.docs, self.hashes, self.records = {}, {}, []
        self.layouts = self.read('translations/text-manager-layouts.json', {})
        self.status = self.read('translations/text-manager-status.json', {})
        self.reload()

    def read(self, rel, default=None):
        if rel not in self.docs:
            path = self.root/rel
            data = path.read_bytes() if path.exists() else None
            self.hashes[rel] = hashlib.sha256(data).hexdigest() if data is not None else None
            self.docs[rel] = json.loads(data.decode('utf-8')) if data is not None else default
        return self.docs[rel]

    def add(self, group, key, source, text, reviewed, file, kind='dict', category='', profile=None, meta=None):
        uid = file + ':' + str(key)
        profile = profile or Profile()
        if uid in self.layouts:
            profile = Profile(**self.layouts[uid])
        if group in ('전투 문장','전투 기술·대사') and profile.font=='large':
            profile=replace(profile,font='battle')
        if category=='monster_dialogue' and 'newline_pages' not in self.layouts.get(uid,{}):
            profile=monster_popup_profile(profile)
        if group=='전투 문장' and (meta or {}).get('category')=='attack_message' and (meta or {}).get('index') in (48,49):
            profile=replace(profile,numeric_pixels=60)
        reviewed = self.status.get(uid, reviewed)
        record = Record(uid, group, str(key), source, text, reviewed, file, kind, category, profile, tuple(CONTROL.findall(text)), meta or {})
        record.baseline_printf = tuple(PRINTF.findall(text))
        self.records.append(record)

    def reload(self):
        self.records = []
        original = self.read('analysis/dialogue-original.json', [])
        manual = self.read('translations/manual_dialogue.json', {})
        draft = self.read('translations/dialogue.ko.json', {})
        for row in original:
            key = str(row['id']); text = manual[key] if key in manual else draft.get(key, {}).get('translation', '')
            self.add('대사', key, row['source'], text, key in manual, 'translations/manual_dialogue.json', 'main', profile=Profile(center=row['id'] in (6, 7, 8, 9)))
        for filename, group, original_name in [
            ('descriptions.ko.json', '설명문', 'descriptions-original.json'),
            ('battle-abilities.ko.json', '전투 기술·대사', 'battle-abilities-original.json'),
            ('battle-messages.ko.json', '전투 문장', 'battle-messages-original.json'),
            ('fixed-catalog.ko.json', '이름·도구·마법', 'fixed-catalog-original.json'),
            ('menu-labels.ko.json', '메뉴 글씨', 'menu-labels-original.json'),
            ('menu-jobs.ko.json', '직업', ''),
            ('omake.ko.json', '부록 문장', 'omake-original.json'),
            ('psx-ui-messages.ko.json', 'PSX 저장·불러오기', 'psx-ui-messages-original.json'),
            ('psx-small-labels.ko.json', 'PSX 작은 글씨', ''),
            ('boost-options.ko.json', '부스트 설정', ''),
        ]:
            path = 'translations/' + filename
            rows = self.read(path, {})
            originals = {str(r['id']): r for r in self.read('analysis/'+original_name, [])} if original_name else {}
            for key, row in rows.items():
                src = originals.get(key, {})
                profile = Profile()
                category = src.get('category', '')
                if group in ('이름·도구·마법', '메뉴 글씨', '직업', 'PSX 작은 글씨'):
                    profile = Profile('small', 96, 1, 8, False, note='작은 글씨 8px, 공백 4px. 기본 폭 96px은 보수적 참고값.')
                    if src.get('encoding') == 'bigText':
                        profile = Profile('large', 216, 1, 12, False, note='큰 이름 글씨. 화면별 칸 폭은 별도 확인.')
                    if group == '메뉴 글씨':
                        x = src.get('position', {}).get('x', 0)
                        profile.width = max(8, (32-x)*8)
                        profile.note = '원래 배치 X에서 256px 화면 끝까지. 이웃 칸 경계는 별도 확인.'
                elif group == '설명문':
                    if category=='esper_description':
                        profile = Profile('large',120,1,16,False,confirmed=True,note='실제 환수 목록·특수 화면의 한 줄 요약. 보수적 폭 120px, 줄바꿈 불가.')
                    else:
                        profile = Profile('large',216,2,16,False,note='도구·마법의 위쪽 설명 영역 216px/2줄. 다른 출력 경로도 확인.')
                elif group in ('전투 기술·대사', '전투 문장'):
                    profile = Profile('battle', 216, 4, 16, False, note='전투 큰 글씨는 영문·문장부호도 12px, 공백 6px. 세부 출력 경로는 별도 확인.')
                elif group == '부록 문장':
                    profile = Profile('bonus', 216, 6, 12, True, confirmed=89 <= int(key) <= 521, note='부록 설명 216px, 최대 6줄. 제목 등은 별도 확인.')
                elif group == 'PSX 저장·불러오기':
                    profile = Profile('psx', 240, 5, 16, False, note='저장 화면별 메시지 칸은 별도 확인.')
                elif group == '부스트 설정':
                    profile = Profile('small',BOOST_WIDTHS[key],1,8,False,confirmed=True,note='부스트 설정의 실제 고정 칸. 갈무리7, 반각 공백 4px, 한 줄 유지.')
                self.add(group, key, row.get('source', src.get('source', '')), row['translation'], row.get('status', '').startswith('manual'), path, category=category, profile=profile, meta=src)
        for filename, group in [('map-titles.json', '지역명'), ('psx_auxiliary.json', 'PSX 도움말')]:
            for i, row in enumerate(self.read('translations/'+filename, [])):
                key = row.get('id', i)
                self.add(group, key, row.get('source', ''), row['translation'], True, 'translations/'+filename, 'list', profile=Profile(rows=1, auto_wrap=False) if group == '지역명' else Profile(), meta={'index': i, **row})
        small = self.read('translations/omake-small.ko.json', {'strings': [], 'records': []})
        for i, text in enumerate(small['strings']):
            sources = sorted({r['source'] for r in small['records'] if i in r.get('reference_ids', [])})
            self.add('부록 작은 글씨', i, '\n'.join(sources), text, True, 'translations/omake-small.ko.json', 'small', profile=Profile('small', 128, 1, 8, False, note='부록 작은 글씨. 화면마다 경계가 달라 별도 확인.'))
        for i, row in enumerate(self.read('translations/movie-subtitles.ko.json', [])):
            self.add('동영상 자막', i, row.get('source', ''), row['translation'], row.get('status') == 'manual', 'translations/movie-subtitles.ko.json', 'list', profile=Profile('subtitle', 304, 2, 14, False, center=True, confirmed=True, note='별도 자막 12×12, 각 줄 304px, 최대 2줄. OPEN/OPERA/END 영상 프레임 기준.'), meta={'index': i, **row})
        gallery=self.read('translations/gallery-text.ko.json',[])
        validate_gallery_rows(gallery)
        for i,row in enumerate(gallery):
            self.add('갤러리 설명',row['id'],row['source'],row['translation'],row.get('status')=='manual',
                'translations/gallery-text.ko.json','list',profile=gallery_profile(row),meta={'index':i,**row})
        self.by_uid = {r.uid: r for r in self.records}

    def commit(self, changed):
        """Detect external edits, back up every file, and atomically replace it.

        A per-project exclusive lock prevents two editor instances from racing.
        If replacement fails midway, restore all files already replaced.
        """
        lock = self.root/'translations/.text-manager-save.lock'
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            raise ConflictError('다른 저장 작업이 진행 중입니다. 잠시 후 다시 저장하세요.')
        try:
            os.write(fd, str(os.getpid()).encode()); os.close(fd)
            for rel in changed:
                path = self.root/rel
                current = hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None
                if current != self.hashes.get(rel):
                    raise ConflictError(f'외부에서 파일이 변경됐습니다: {rel}\n내용을 복사해 둔 뒤 프로젝트를 다시 여세요.')
            stamp = datetime.now().strftime('%Y%m%d-%H%M%S-') + uuid.uuid4().hex[:8]
            backup = self.root/'work/text-manager-backups'/stamp
            backup.mkdir(parents=True)
            existed, temporary, replaced = {}, {}, []
            for rel, obj in changed.items():
                target = self.root/rel; target.parent.mkdir(parents=True, exist_ok=True)
                existed[rel] = target.exists()
                if target.exists():
                    dest = backup/rel; dest.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(target, dest)
                tmp = target.with_name(target.name+'.'+uuid.uuid4().hex+'.tmp')
                with tmp.open('w', encoding='utf-8', newline='\n') as handle:
                    json.dump(obj, handle, ensure_ascii=False, indent=2); handle.write('\n'); handle.flush(); os.fsync(handle.fileno())
                temporary[rel] = tmp
            (backup/'manifest.json').write_text(json.dumps({'existing_files': existed}, ensure_ascii=False, indent=2), 'utf-8')
            try:
                for rel, tmp in temporary.items():
                    os.replace(tmp, self.root/rel); replaced.append(rel)
            except Exception:
                for rel in reversed(replaced):
                    if existed[rel]:
                        shutil.copy2(backup/rel, self.root/rel)
                    else:
                        (self.root/rel).unlink(missing_ok=True)
                raise
            finally:
                for tmp in temporary.values():
                    tmp.unlink(missing_ok=True)
            for rel, obj in changed.items():
                self.docs[rel] = obj
                self.hashes[rel] = hashlib.sha256((self.root/rel).read_bytes()).hexdigest()
            return backup
        finally:
            lock.unlink(missing_ok=True)

    def import_bonus_small(self, bank, metrics):
        """Register discovered bonus literals without losing existing string IDs."""
        import copy
        bank=copy.deepcopy(bank)
        old=self.read('translations/omake-small.ko.json',{'strings':[],'records':[]})
        if bank['strings'][:len(old['strings'])]!=old['strings'] or bank['records'][:len(old['records'])]!=old['records']:
            raise ValueError('기존 부록 항목은 유지하고 새 항목을 추가해야 합니다.')
        original=(self.root/'work/decompressed/OMAKEDIR/OMAKE.PAC').read_bytes()
        used=set()
        for i,row in enumerate(bank['records']):
            at=row['offset'];size=row['length'];raw=bytes.fromhex(row['raw_hex'])+b'\0'
            patched=bytes.fromhex(row['patched_hex'])
            if row['id']!=i or at<0 or at+size>len(original) or len(raw)>size or original[at:at+len(raw)]!=raw:
                raise ValueError('부록 원문 위치가 일치하지 않습니다.')
            if not patched.endswith(b'\0') or len(patched)>size or any(p in used for p in range(at,at+size)):
                raise ValueError('부록 문자열의 저장 공간이 겹칩니다.')
            used.update(range(at,at+size))
            if any(not 0<=ref<len(bank['strings']) for ref in row['reference_ids']):
                raise ValueError('부록 번역 참조가 잘못되었습니다.')
        for i,text in enumerate(bank['strings']):
            row=Record('bonus-small:'+str(i),'부록 작은 글씨',str(i),'',text,True,
                'translations/omake-small.ko.json',profile=Profile('small',128,1,8,False))
            errors=[v.message for v in metrics.check(row)[0] if v.severity=='오류']
            if errors:raise ValueError('\n'.join(errors))
        backup=self.commit({'translations/omake-small.ko.json':bank})
        self.reload();return backup

    def import_subtitles(self, rows, metrics):
        """Register or replace a complete timed cue list through the editor."""
        import copy
        validate_caption_rows(rows)
        rows=copy.deepcopy(rows)
        for i,row in enumerate(rows):
            row.setdefault('movie','OPERA')
            row.setdefault('status','editor_draft')
            record=Record('caption:'+str(i),'동영상 자막',str(i),row['source'],row['translation'],True,
                'translations/movie-subtitles.ko.json',profile=Profile('subtitle',304,2,14,False,center=True,confirmed=True),meta=row)
            issues,_,_=metrics.check(record)
            errors=[v.message for v in issues if v.severity=='오류']
            if errors:raise ValueError('\n'.join(errors))
        layouts=copy.deepcopy(self.layouts);status=copy.deepcopy(self.status)
        prefix='translations/movie-subtitles.ko.json:'
        layouts={k:v for k,v in layouts.items() if not k.startswith(prefix)}
        status={k:v for k,v in status.items() if not k.startswith(prefix)}
        self.read('translations/movie-subtitles.ko.json',[])
        backup=self.commit({'translations/movie-subtitles.ko.json':rows,
            'translations/text-manager-layouts.json':layouts,'translations/text-manager-status.json':status})
        self.layouts=layouts;self.status=status;self.reload()
        return backup

    def save(self, record, text, reviewed, profile, metrics):
        return self.save_many([(record, text, reviewed, profile)], metrics)

    def import_boost(self, rows, metrics):
        """Register boost-page prose through the same backed-up EXE workflow."""
        import copy
        rows=copy.deepcopy(rows);validate_boost_rows(rows)
        for key,row in rows.items():
            p=Profile('small',BOOST_WIDTHS[key],1,8,False,confirmed=True)
            r=Record('boost:'+key,'부스트 설정',key,row.get('source',''),row['translation'],True,
                'translations/boost-options.ko.json',profile=p)
            issues,_,_=metrics.check(r)
            errors=[i.message for i in issues if i.severity=='오류']
            if errors:raise ValueError(key+'\n'+'\n'.join(errors))
            row['status']='manual'
        self.read('translations/boost-options.ko.json',{})
        backup=self.commit({'translations/boost-options.ko.json':rows})
        self.reload();return backup

    def import_gallery(self, rows, metrics):
        """Validate and register the whole static-gallery text catalog."""
        import copy
        validate_gallery_rows(rows);rows=copy.deepcopy(rows)
        for row in rows:
            record=Record('gallery:'+str(row['id']),'갤러리 설명',str(row['id']),row['source'],row['translation'],True,
                'translations/gallery-text.ko.json',profile=gallery_profile(row),meta=row)
            issues,effective,_=metrics.check(record)
            errors=[i.message for i in issues if i.severity=='오류']
            if errors:raise ValueError(str(row['id'])+'\n'+'\n'.join(errors))
            row['translation']=effective;row['status']='manual'
        self.read('translations/gallery-text.ko.json',[])
        layouts=copy.deepcopy(self.layouts);status=copy.deepcopy(self.status)
        prefix='translations/gallery-text.ko.json:'
        layouts={k:v for k,v in layouts.items() if not k.startswith(prefix)}
        status={k:v for k,v in status.items() if not k.startswith(prefix)}
        backup=self.commit({'translations/gallery-text.ko.json':rows,
            'translations/text-manager-layouts.json':layouts,'translations/text-manager-status.json':status})
        self.layouts=layouts;self.status=status;self.reload()
        return backup

    def save_many(self, items, metrics):
        """Validate the entire import before changing any canonical file."""
        import copy
        changed = {}; planned = []; seen = set()
        for record, text, reviewed, profile in items:
            if record.uid in seen: raise ValueError('중복된 가져오기 ID: '+record.uid)
            seen.add(record.uid)
            actual_text = self.plan_save(record, text, reviewed, profile, metrics, changed)
            planned.append((record, actual_text, reviewed, replace(profile)))
        if not planned: raise ValueError('저장할 항목이 없습니다.')
        if 'translations/movie-subtitles.ko.json' in changed:
            validate_caption_rows(changed['translations/movie-subtitles.ko.json'])
        backup = self.commit(changed)
        self.layouts = self.docs['translations/text-manager-layouts.json']
        self.status = self.docs['translations/text-manager-status.json']
        for record, text, reviewed, profile in planned:
            record.text = text; record.reviewed = reviewed; record.profile = profile
        return backup

    def plan_save(self, record, text, reviewed, profile, metrics, changed):
        if not isinstance(text, str) or not isinstance(reviewed, bool):
            raise ValueError('번역은 문자열, 검수 상태는 true/false여야 합니다.')
        issues, effective, _ = metrics.check(record, text, profile)
        structural = {'controls', 'braces', 'printf', 'space', 'composition', 'control_character', 'timing', 'caption_length', 'caption_layout', 'font_path', 'name_length','gallery_bounds','psx_literal_capacity','boost_bounds'}
        if record.group=='갤러리 설명':structural|={'width','height','pitch'}
        fatal = [i for i in issues if i.severity == '오류' and i.code in structural]
        if fatal:
            raise ValueError(record.uid+'\n'+'\n'.join(i.message for i in fatal))
        # Custom narrow boxes must not only look wrapped in the preview: persist
        # the same line breaks so the next ROM build uses the checked layout.
        if profile.auto_wrap:
            text = effective
        # Work on copies so a failed/conflicting save cannot modify the open store.
        import copy
        def doc(rel, default=None):
            if rel not in changed:
                changed[rel] = copy.deepcopy(self.read(rel, default))
            return changed[rel]
        key = record.key
        if record.kind == 'main':
            manual = doc('translations/manual_dialogue.json', {})
            if reviewed:
                manual[key] = text
            else:
                manual.pop(key, None)
                draft = doc('translations/dialogue.ko.json', {})
                old = draft.get(key, {})
                draft[key] = {**old, 'source': record.source, 'translation': text, 'status': 'machine_draft'}
        elif record.kind == 'small':
            doc(record.file)['strings'][int(key)] = text
        elif record.kind == 'list':
            row = doc(record.file)[record.meta['index']]
            row['translation'] = text; row['status'] = 'manual' if reviewed else 'editor_draft'
        else:
            row = doc(record.file)[key]
            row['translation'] = text; row['status'] = 'manual' if reviewed else 'editor_draft'
            if record.group == '부록 문장':
                doc('translations/omake-manual.json', {})[key] = text
        doc('translations/text-manager-layouts.json', {})[record.uid] = asdict(profile)
        doc('translations/text-manager-status.json', {})[record.uid] = reviewed
        return text

    def import_items(self, rows):
        if isinstance(rows, dict): rows = rows.get('records', [])
        if not isinstance(rows, list): raise ValueError('JSON 항목 목록이 필요합니다.')
        items=[]; seen=set()
        for row in rows:
            uid=row['uid']
            if uid in seen: raise ValueError('중복된 가져오기 ID: '+uid)
            seen.add(uid)
            if uid not in self.by_uid: raise ValueError('알 수 없는 가져오기 ID: '+uid)
            r=self.by_uid[uid]
            if 'source' in row and row['source']!=r.source: raise ValueError('원문이 다른 항목입니다: '+uid)
            p=Profile(**row['profile']) if 'profile' in row else replace(r.profile)
            if r.group in ('전투 문장','전투 기술·대사') and p.font=='large':
                p=replace(p,font='battle')
            if not (8<=p.width<=640 and 1<=p.rows<=40 and 8<=p.pitch<=48):
                raise ValueError('검사 영역 값이 범위를 벗어났습니다: '+uid)
            items.append((r,row['translation'],row.get('reviewed',r.reviewed),p))
        return items


def audit(store, metrics):
    metrics.refresh_variables(store.records)
    results = []
    for r in store.records:
        issues, _, lines = metrics.check(r)
        results.append({'uid': r.uid, 'group': r.group, 'id': r.key, 'reviewed': r.reviewed,
                        'translation': r.text, 'profile': asdict(r.profile),
                        'max_width': max((l.width for l in lines), default=0),
                        'issues': [asdict(i) for i in issues]})
    captions=[dict(r.meta,translation=r.text) for r in store.records if r.group=='동영상 자막']
    try:validate_caption_rows(captions)
    except (ValueError,KeyError,TypeError) as e:
        for row in results:
            if row['group']=='동영상 자막':row['issues'].append(asdict(Issue('오류','caption_bank',str(e))))
    return results


def write_report(path, results):
    path = Path(path)
    if path.suffix.lower() == '.csv':
        with path.open('w', encoding='utf-8-sig', newline='') as handle:
            writer = csv.writer(handle); writer.writerow(['분류', 'ID', '검수', '폭(px)', '문제', '번역'])
            for row in results:
                writer.writerow([row['group'], row['id'], '완료' if row['reviewed'] else '초안', row['max_width'], ' / '.join(i['message'] for i in row['issues'] if i['severity'] != '참고'), row['translation']])
    else:
        path.write_text(json.dumps(results, ensure_ascii=False, indent=2)+'\n', 'utf-8')
