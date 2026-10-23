"""Meaningful layout parity, save-safety and standalone-data tests."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from text_manager_model import Store, Metrics, Profile, Record, ConflictError, audit, write_report, monster_popup_profile

ROOT = Path(__file__).resolve().parents[1]


class TextManagerTests(unittest.TestCase):
    def test_space_at_exact_line_edge_preserves_word_boundary(self):
        from textlayout import wrap as native_wrap
        # Previously the trailing space triggered a backtrack, then vanished,
        # joining the carried word to the next one on the following line.
        text='가나 다라 마바'
        expected='가나 다라\n마바'
        self.assertEqual(self.metrics.wrap(text,Profile(width=54),safe=True),expected)
        self.assertEqual(native_wrap(text,{},set('가나다라마바'),[],limit=54),expected)
        for width in range(24,217,6):
            result=self.metrics.wrap(text,Profile(width=width),safe=True)
            self.assertEqual(result.split(),text.split())

    def test_bonus_discovery_import_guards_original_and_existing_ids(self):
        path=self.root/'work/decompressed/OMAKEDIR/OMAKE.PAC'
        path.parent.mkdir(parents=True);path.write_bytes(b'%k\xcd\xde\xbd\xc4\0')
        bank={'strings':['최고'],'records':[dict(id=0,offset=0,length=7,source='ベスト',
            raw_hex='256bcddebdc4',patched_hex='256b018000',reference_ids=[0])]}
        self.store.import_bonus_small(bank,self.metrics)
        self.assertEqual(Store(self.root).by_uid['translations/omake-small.ko.json:0'].text,'최고')
        import copy
        bad=copy.deepcopy(bank);bad['strings'][0]='다른 항목'
        with self.assertRaises(ValueError):self.store.import_bonus_small(bad,self.metrics)
        bad=copy.deepcopy(bank);bad['records'].append(dict(bad['records'][0],id=1))
        with self.assertRaises(ValueError):self.store.import_bonus_small(bad,self.metrics)

    def test_native_boost_catalog_fixed_columns_and_import_backup(self):
        from boost_format import WIDTHS
        rows={key:{'source':key,'translation':'가' if width==8 else '검사'} for key,width in WIDTHS.items()}
        self.store.import_boost(rows,self.metrics)
        record=self.store.by_uid['translations/boost-options.ko.json:encounter']
        self.assertEqual((record.group,record.profile.width,record.profile.space),('부스트 설정',80,4))
        with self.assertRaises(ValueError):
            self.store.save(record,'가'*11,True,record.profile,self.metrics)
        self.assertEqual(Store(self.root).by_uid[record.uid].text,'검사')
        rows['on']['translation']='가'*4
        with self.assertRaises(ValueError):self.store.import_boost(rows,self.metrics)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root/'translations').mkdir(); (self.root/'analysis').mkdir()
        self.put('project-settings.json', {})
        self.put('analysis/dialogue-original.json', [{'id': 0, 'source': '「原文{page}本文。{key}'}, {'id': 1, 'source': '名前'}])
        self.put('translations/manual_dialogue.json', {'0': '「첫 문장.{page}다음 문장.{key}'})
        self.put('translations/dialogue.ko.json', {'1': {'source': '名前', 'translation': '이름', 'status': 'machine_draft'}})
        self.put('translations/omake.ko.json', {'89': {'source': '説明', 'translation': '설명입니다.', 'status': 'manual'}})
        self.put('translations/omake-manual.json', {'89': '설명입니다.'})
        self.store = Store(self.root)
        self.metrics = Metrics()

    def tearDown(self):
        self.tmp.cleanup()

    def put(self, rel, value):
        p = self.root/rel; p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(value, ensure_ascii=False), 'utf-8')

    def row(self, key='0'):
        return next(r for r in self.store.records if r.kind=='main' and r.key==key)

    def test_native_spaces_dynamic_name_and_center(self):
        p = Profile(width=216, center=True)
        _, lines = self.metrics.layout('가 나{char00}', p)
        self.assertEqual(lines[0].width, 12+6+12+72)
        self.assertEqual(lines[0].offset, 60)
        self.assertEqual(self.metrics.advance(' ', Profile(font='small')), 4)
        self.assertEqual(self.metrics.advance('한', Profile(font='small')), 8)

    def test_horizontal_and_vertical_overflow(self):
        p = Profile(width=24, rows=1, auto_wrap=False, confirmed=True)
        r = self.row()
        issues, _, _ = self.metrics.check(r, '「너무 깁니다.{page}둘째\n셋째{key}', p)
        self.assertTrue(any(i.code=='width' and i.severity=='오류' for i in issues))
        self.assertTrue(any(i.code=='height' and i.severity=='오류' for i in issues))

    def test_monster_popup_uses_native_sequential_lines_and_full_size(self):
        text='첫 문장...{pause}\n다음 문장.{pause}\n끝 문장.{pause}'
        profile=monster_popup_profile()
        record=Record('popup','전투 기술·대사','0','',text,True,'',category='monster_dialogue',
                      profile=profile,baseline_controls=tuple(['{pause}']*3))
        issues,_,lines=self.metrics.check(record)
        self.assertFalse(any(i.severity=='오류' for i in issues))
        self.assertEqual([(line.page,line.number) for line in lines],[(1,1),(2,1),(3,1)])
        self.assertEqual(lines[0].width,6*12+6)
        self.assertEqual((profile.cell,profile.space,profile.rows),(12,6,1))
        for bad in [Profile('battle',216,4,16,False),
                    Profile('battle',216,1,16,True,newline_pages=True)]:
            self.assertTrue(any(i.code in ('popup_flow','popup_wrap') for i in self.metrics.check(record,profile=bad)[0]))
        overflow='가'*19+'{pause}\n다음.{pause}\n끝.{pause}'
        self.assertTrue(any(i.code=='width' for i in self.metrics.check(record,overflow)[0]))

    def test_monster_popup_legacy_profile_migrates_without_text_edits(self):
        self.put('analysis/battle-abilities-original.json',[dict(id=0,category='monster_dialogue',index=0,source='原文')])
        self.put('translations/battle-abilities.ko.json',{'0':dict(source='原文',translation='한 문장.{pause}\n다음.{pause}',status='manual')})
        uid='translations/battle-abilities.ko.json:0'
        self.put('translations/text-manager-layouts.json',{uid:dict(font='battle',width=204,rows=4,pitch=16,auto_wrap=False)})
        before=(self.root/'translations/battle-abilities.ko.json').read_bytes()
        store=Store(self.root);record=store.by_uid[uid]
        self.assertTrue(record.profile.newline_pages)
        self.assertEqual((record.profile.width,record.profile.rows),(204,1))
        self.assertEqual((self.root/record.file).read_bytes(),before)

    def test_legacy_icon_metrics_do_not_draw_pause_control_cells(self):
        metrics=Metrics({'icons':['{pause}','{key}','{color}','{sword}']})
        for font in ('large','battle','small'):
            profile=Profile(font=font)
            for token in ('{pause}','{key}','{color}'):
                self.assertEqual(metrics.advance(token,profile),0)
            self.assertEqual(metrics.advance('{sword}',profile),profile.cell)

    def test_battle_inline_key_preserves_native_cursor_and_field_behavior(self):
        p=Profile('battle',216,4,16,False)
        text='이 녀석은...{pause}{key} 생각났어!{key}'
        _,lines=self.metrics.layout(text,p)
        self.assertEqual([(line.page,line.number,line.width) for line in lines],[(1,1,156)])
        # Field keys retain their separate page semantics and builder parity.
        _,field=self.metrics.layout(text,Profile(auto_wrap=False))
        self.assertEqual([line.page for line in field],[1,2])

    def test_battle_inline_key_cannot_hide_combined_overflow(self):
        text='가'*10+'{key}'+'나'*9
        p=Profile('battle',216,4,16,False)
        record=Record('inline','전투 기술·대사','0','',text,True,'',profile=p,baseline_controls=('{key}',))
        issues,_,lines=self.metrics.check(record)
        self.assertEqual(lines[0].width,228)
        self.assertTrue(any(i.code=='width' and i.severity=='오류' for i in issues))

    def test_battle_inline_wait_wrap_preserves_controls_and_actual_line_width(self):
        text='가'*10+'{key}'+'나'*9
        p=Profile('battle',216,4,16,True)
        effective,lines=self.metrics.layout(text,p)
        self.assertIn('\n',effective)
        self.assertEqual(effective.replace('\n',''),text)
        self.assertEqual([line.width for line in lines],[216,12])

    def test_auto_wrap_does_not_hide_single_oversize_variable(self):
        r = Record('x', '대사', '0', '', '{char00}', False, '', baseline_controls=('{char00}',), profile=Profile(width=24))
        issues, _, _ = self.metrics.check(r)
        self.assertTrue(any(i.code=='width' for i in issues))

    def test_controls_and_fullwidth_space_cannot_be_saved(self):
        r = self.row()
        for text in ['제어 코드 삭제', '첫\u3000문장.{page}다음 문장.{key}']:
            with self.assertRaises(ValueError):
                self.store.save(r, text, True, r.profile, self.metrics)
        self.assertEqual(json.loads((self.root/r.file).read_text('utf-8'))['0'], r.text)

    def test_backup_canonical_main_and_review_status(self):
        r = self.row('1')
        backup = self.store.save(r, '수정한 이름', True, r.profile, self.metrics)
        self.assertTrue((backup/'translations/manual_dialogue.json').exists())
        loaded = Store(self.root)
        actual = next(r for r in loaded.records if r.kind=='main' and r.key=='1')
        self.assertEqual(actual.text, '수정한 이름'); self.assertTrue(actual.reviewed)
        loaded.save(actual, '초안 이름', False, actual.profile, self.metrics)
        self.assertNotIn('1', json.loads((self.root/'translations/manual_dialogue.json').read_text('utf-8')))
        self.assertEqual(Store(self.root).records[1].text, '초안 이름')

    def test_bonus_dual_sources_stay_in_sync(self):
        r = next(r for r in self.store.records if r.group=='부록 문장')
        self.store.save(r, '함께 저장됩니다.', True, r.profile, self.metrics)
        ko = json.loads((self.root/r.file).read_text('utf-8'))
        manual = json.loads((self.root/'translations/omake-manual.json').read_text('utf-8'))
        self.assertEqual(ko['89']['translation'], manual['89'])

    def test_external_edit_detected_without_overwrite(self):
        r = self.row(); self.put(r.file, {'0': '외부 변경'})
        with self.assertRaises(ConflictError):
            self.store.save(r, '첫 수정.{page}다음 수정.{key}', True, r.profile, self.metrics)
        self.assertEqual(json.loads((self.root/r.file).read_text('utf-8'))['0'], '외부 변경')

    def test_failed_multifile_replace_rolls_back(self):
        import os
        before = (self.root/'translations/manual_dialogue.json').read_bytes()
        real_replace = os.replace; calls = []
        def failing(src, dest):
            calls.append(dest)
            if len(calls)==2: raise OSError('simulated locked file')
            return real_replace(src, dest)
        r = self.row()
        with patch('text_manager_model.os.replace', side_effect=failing):
            with self.assertRaises(OSError):
                self.store.save(r, '첫 수정.{page}다음 수정.{key}', True, r.profile, self.metrics)
        self.assertEqual((self.root/r.file).read_bytes(), before)
        self.assertFalse((self.root/'translations/.text-manager-save.lock').exists())

    def test_report_export(self):
        results = audit(self.store, self.metrics)
        for name in ['report.json', 'report.csv']:
            write_report(self.root/name, results)
            self.assertGreater((self.root/name).stat().st_size, 100)

    def test_custom_narrow_wrap_is_persisted(self):
        r = self.row('1'); p = Profile(width=36, rows=10)
        self.store.save(r, '가나다라마바사', True, p, self.metrics)
        self.assertEqual(Store(self.root).records[1].text, '가나다\n라마바\n사')

    def test_printf_variable_preserved(self):
        r = Record('x', 'PSX 작은 글씨', '0', '', '슬롯 %d', True, '', profile=Profile(font='small'), baseline_printf=('%d',))
        issues, _, _ = self.metrics.check(r, '슬롯 %s')
        self.assertTrue(any(i.code=='printf' for i in issues))

    def test_variable_catalog_and_unsaved_long_name(self):
        item = Record('item', '이름·도구·마법', '0', '', '짧음', True, '', category='item')
        m = Metrics(); m.refresh_variables([item], {'item': '아주 길어진 도구 이름'})
        width = sum(6 if c==' ' else 12 for c in '아주 길어진 도구 이름')
        self.assertEqual(m.advance('{item}', Profile()), width)
        self.assertEqual(m.advance('{item[00]}', Profile()), width)
        self.assertEqual(m.wrap('{item}', Profile(width=80), safe=True), '{item}')
        r = Record('x', '대사', '0', '', '{item}', True, '', profile=Profile(width=80), baseline_controls=('{item}',))
        self.assertTrue(any(i.code=='width' for i in m.check(r)[0]))

    def test_middle_dot_is_punctuation_not_japanese_residual(self):
        r = Record('x', '대사', '0', '', '도・둑・질?', True, '', profile=Profile())
        self.assertFalse(any(i.code=='japanese' for i in self.metrics.check(r)[0]))
        self.assertTrue(any(i.code=='japanese' for i in self.metrics.check(r, '日本語')[0]))

    def test_large_text_cannot_be_checked_as_small_to_hide_overflow(self):
        r=self.row()
        with self.assertRaises(ValueError):
            self.store.save(r, r.text, True, Profile(font='small'), self.metrics)

    def test_batch_validation_is_atomic(self):
        first, second=self.row(),self.row('1')
        before=(self.root/first.file).read_bytes()
        with self.assertRaises(ValueError):
            self.store.save_many([(second,'새 이름',True,second.profile),(first,'제어 코드 삭제',True,first.profile)],self.metrics)
        self.assertEqual((self.root/first.file).read_bytes(),before)
        self.assertEqual(second.text,'이름')

    def test_batch_source_guard_and_single_backup(self):
        first,second=self.row(),self.row('1')
        rows=[{'uid':first.uid,'source':first.source,'translation':'첫 수정.{page}다음 수정.{key}','reviewed':True},
              {'uid':second.uid,'source':second.source,'translation':'새 이름','reviewed':True}]
        backup=self.store.save_many(self.store.import_items(rows),self.metrics)
        self.assertTrue((backup/'manifest.json').exists())
        self.assertEqual(len(list((self.root/'work/text-manager-backups').iterdir())),1)
        self.assertEqual(Store(self.root).records[1].text,'새 이름')
        rows[0]['source']='다른 원문'
        with self.assertRaises(ValueError):self.store.import_items(rows)

    def test_duplicate_import_ids_rejected(self):
        r=self.row('1'); row={'uid':r.uid,'translation':'이름'}
        with self.assertRaises(ValueError):self.store.import_items([row,row])

    def test_period_hint_ignores_wrapped_choices_but_keeps_prose(self):
        r = Record('x', '대사', '0', '', '', False, '', profile=Profile())
        for text in ['쉬시겠어요?\n{choice}예\n{choice}아니요',
                     '{choice}다음에\n온다', '{choice}그만둔다{page}돌아왔다.']:
            self.assertFalse(any(i.code=='period' for i in self.metrics.check(r, text)[0]), text)
        for text in ['돌아왔다\n{choice}예\n{choice}아니요',
                     '{choice}그만둔다{page}돌아왔다',
                     '{choice}그만둔다{key[04]}돌아왔다']:
            self.assertTrue(any(i.code=='period' for i in self.metrics.check(r, text)[0]), text)

    def test_response_label_does_not_require_a_terminal_period(self):
        r=Record('answer','PSX 저장·불러오기','18','','아니요',True,'',profile=Profile(font='psx'))
        for text in ('예','아니요','아니오'):
            self.assertFalse(any(i.code=='period' for i in self.metrics.check(r,text)[0]))
        self.assertTrue(any(i.code=='period' for i in self.metrics.check(r,'저장하지 않아도 괜찮아요')[0]))

    def test_fixed_psx_literal_capacity_is_distinct_from_visual_width(self):
        self.put('translations/psx-small-labels.ko.json',{'18':dict(source='%pメモファイル',translation='%p임시본',status='manual')})
        store=Store(self.root);r=store.by_uid['translations/psx-small-labels.ko.json:18']
        issues,_,_=self.metrics.check(r,'%p임시 파일')
        self.assertTrue(any(i.code=='psx_literal_capacity' for i in issues))
        self.assertFalse(any(i.code=='width' for i in issues))
        self.assertFalse(any(i.severity=='오류' for i in self.metrics.check(r)[0]))
        before=(self.root/r.file).read_bytes()
        with self.assertRaises(ValueError):store.save(r,'%p임시 파일',True,r.profile,self.metrics)
        self.assertEqual((self.root/r.file).read_bytes(),before)

    def test_battle_uses_fixed_ascii_advance(self):
        metrics=Metrics({'widths':{'.':4,'A':8}})
        self.assertEqual(metrics.advance('.',Profile()),4)
        self.assertEqual(metrics.advance('.',Profile(font='battle')),12)
        self.assertEqual(metrics.advance('A',Profile(font='battle')),12)
        self.assertEqual(metrics.advance(' ',Profile(font='battle')),6)
        r=Record('x','전투 문장','0','','',True,'',profile=Profile(font='battle'))
        self.assertFalse(any(i.code=='font_path' for i in metrics.check(r,'ABC')[0]))
        self.assertTrue(any(i.code=='font_path' for i in metrics.check(r,'ABC',Profile())[0]))

    def test_typed_battle_strings_and_numeric_bounds(self):
        m=Metrics();p=Profile(font='battle')
        item=Record('item','이름·도구·마법','0','','아주 긴 도구 이름',True,'',category='item')
        m.refresh_variables([item],{'item':'새로 길어진 도구 이름'})
        width=sum(6 if c==' ' else 12 for c in '새로 길어진 도구 이름')
        self.assertEqual(m.advance('{string[00]}',p),72)
        self.assertEqual(m.advance('{string[01]}',p),width)
        self.assertEqual(m.advance('{var0}',p),96)
        self.assertEqual(m.advance('{var1}',Profile(font='battle',numeric_pixels=60)),60)
        self.assertEqual(m.advance('{string[04]}',p),216)

    def test_bonus_description_matches_actual_word_reflow_and_save(self):
        from omake_runtime import wrap
        r=next(r for r in self.store.records if r.group=='부록 문장')
        text='첫 문장입니다.\n\n두 번째 문장도 이어서 출력합니다.'
        expected=wrap(' '.join(text.split()))
        self.assertEqual(self.metrics.check(r,text)[1],expected)
        self.store.save(r,text,True,r.profile,self.metrics)
        self.assertEqual(Store(self.root).by_uid[r.uid].text,expected)
        _,_,lines=self.metrics.check(r,'가'*30)
        self.assertGreater(lines[0].width,r.profile.width)

    def test_all_bonus_preview_strings_match_rom_insertion(self):
        from omake_runtime import wrap
        from korean_codec import normalize
        store=Store(ROOT)
        for r in store.records:
            if r.group!='부록 문장':continue
            text=normalize(r.text).replace('갓파','임프')
            if 89<=int(r.key)<=521:text=' '.join(text.split())
            self.assertEqual(self.metrics.check(r)[1],wrap(text),r.uid)

    def test_description_defaults_follow_native_category(self):
        self.put('analysis/descriptions-original.json',[{'id':0,'category':'item_description'},
            {'id':1,'category':'spell_description'},{'id':2,'category':'esper_description'}])
        self.put('translations/descriptions.ko.json',{str(i):{'translation':'설명','source':''} for i in range(3)})
        rows=[r for r in Store(self.root).records if r.group=='설명문']
        self.assertEqual([(r.profile.width,r.profile.rows) for r in rows],[(216,2),(216,2),(120,1)])

    def test_caption_registration_and_atomic_rejection(self):
        rows=[dict(movie='OPEN',start_frame=10,end_frame=20,source='DIRECTOR',translation='감독\n이름')]
        self.store.import_subtitles(rows,self.metrics)
        r=next(r for r in self.store.records if r.group=='동영상 자막')
        self.assertEqual((r.profile.rows,r.profile.pitch),(2,14))
        self.assertFalse(any(i.severity=='오류' for i in self.metrics.check(r)[0]))
        path=self.root/'translations/movie-subtitles.ko.json';before=path.read_bytes()
        for bad in [rows+[dict(rows[0],start_frame=15,end_frame=25)],
                    [dict(rows[0],translation='가'*26)],
                    [dict(rows[0],translation='첫째\n둘째\n셋째')],
                    [dict(rows[0],movie='UNKNOWN')]]:
            with self.assertRaises(ValueError):self.store.import_subtitles(bad,self.metrics)
            self.assertEqual(path.read_bytes(),before)

        # The ending cinema has its own timeline and bank, including overlaps
        # with OPEN's frame numbers.
        self.store.import_subtitles(rows+[dict(rows[0],movie='END',translation='이 세상에서.')],self.metrics)
        self.assertEqual(len(json.loads(path.read_text('utf8'))),2)

    def test_caption_limit_per_line_and_bank_capacity(self):
        from caption_format import pack_caption_text
        row=dict(movie='OPEN',start_frame=10,end_frame=20,source='source',translation='가'*24+'\n'+'나'*24)
        self.store.import_subtitles([row],self.metrics)
        r=next(r for r in self.store.records if r.group=='동영상 자막')
        self.assertFalse(any(i.code=='caption_length' for i in self.metrics.check(r)[0]))
        # A corpus can fit every line yet exceed the shared font bank.
        huge=[dict(row,start_frame=i*2,end_frame=i*2+1,
            translation=''.join(chr(0xac00+i*24+j) for j in range(24))) for i in range(8)]
        with self.assertRaises(ValueError):pack_caption_text(huge)

    def test_caption_edit_revalidates_whole_movie_bank(self):
        rows=[dict(movie='OPEN',start_frame=i*2,end_frame=i*2+1,source='source',translation='가'*24) for i in range(8)]
        self.store.import_subtitles(rows,self.metrics)
        records=[r for r in self.store.records if r.group=='동영상 자막']
        items=[(r,''.join(chr(0xac00+i*24+j) for j in range(24)),True,r.profile) for i,r in enumerate(records)]
        before=(self.root/'translations/movie-subtitles.ko.json').read_bytes()
        with self.assertRaises(ValueError):self.store.save_many(items,self.metrics)
        self.assertEqual((self.root/'translations/movie-subtitles.ko.json').read_bytes(),before)
        for record,text,_,_ in items:record.text=text
        self.assertTrue(all(any(i['code']=='caption_bank' for i in r['issues']) for r in audit(self.store,self.metrics) if r['group']=='동영상 자막'))

    def test_character_name_limit_matches_native_save_and_composer(self):
        self.put('analysis/fixed-catalog-original.json',[{'id':0,'category':'character','encoding':'smallText'}])
        self.put('translations/fixed-catalog.ko.json',{'0':{'source':'ティナ','translation':'티나'}})
        store=Store(self.root);r=next(r for r in store.records if r.category=='character')
        self.assertFalse(any(i.code=='name_length' for i in self.metrics.check(r,'한 글A!?')[0]))
        before=(self.root/r.file).read_bytes()
        for text in ['일곱글자이름칸','한\n글']:
            with self.assertRaises(ValueError):store.save(r,text,True,r.profile,self.metrics)
            self.assertEqual((self.root/r.file).read_bytes(),before)

    def test_current_project_wrap_matches_rom_builder(self):
        from textlayout import wrap
        from korean_codec import font_index
        data = json.loads((ROOT/'assets/text-manager/text-metrics.json').read_text('utf-8'))
        metrics = Metrics(data)
        enc = json.loads((ROOT/'work/korean_encoding.json').read_text('utf-8'))
        mapping = {c: bytes.fromhex(v) for c,v in enc['mapping'].items()}
        assigned = {c: mapping[c] for c in enc['replaced']}
        widths = bytearray((ROOT/'work/extracted/NAR/NAR_BIN.BIN').read_bytes()[0x646d0:0x64bd0])
        for c, code in mapping.items():
            if c not in assigned and c in data['widths']:
                widths[font_index(code)+32] = data['widths'][c]
        store = Store(ROOT)
        for r in store.records:
            if r.group not in ('대사', 'PSX 도움말'): continue
            self.assertEqual(metrics.wrap(r.text, Profile()), wrap(r.text, mapping, assigned, widths), r.uid)

    def test_gallery_import_wrap_backup_and_fixed_art_bounds(self):
        rows=[dict(id='opening-1',file='OMAKEDIR/GALLERY2.BIN',image=0,rect=[260,50,100,60],
            source='原画の説明',translation='그림을 보존하고 글자 영역만 수정합니다.')]
        backup=self.store.import_gallery(rows,self.metrics)
        r=next(r for r in self.store.records if r.group=='갤러리 설명')
        self.assertTrue(backup.exists());self.assertTrue(r.reviewed)
        self.assertEqual(r.profile.font,'small');self.assertEqual(r.profile.width,100)
        self.assertIn('\n',r.text)
        before=(self.root/r.file).read_bytes()
        for p,text in [(Profile('small',120,6,10,True,confirmed=True),'영역 초과'),
                       (Profile('small',100,6,10,False,confirmed=True),'가'*20),
                       (Profile('small',100,6,10,False,confirmed=True),'\n'.join(['줄']*7))]:
            with self.assertRaises(ValueError):self.store.save(r,text,True,p,self.metrics)
            self.assertEqual((self.root/r.file).read_bytes(),before)

    def test_gallery_metadata_rejects_overlap_and_other_files(self):
        row=dict(id='a',file='OMAKEDIR/GALLERY2.BIN',image=0,rect=[260,50,100,60],source='原画',translation='설명입니다.')
        for rows in [[row,dict(row,id='b')],[dict(row,file='../other.bin')],
                     [dict(row,image=18)],[dict(row,rect=[630,470,50,20])],
                     [dict(row,erase_rects=[])],[dict(row,erase_rects=[[630,0,11,8]])],
                     [dict(row,erase_rects=[[1,2,'3',4]])],[dict(row,erase_sample_x=640)]]:
            with self.assertRaises(ValueError):self.store.import_gallery(rows,self.metrics)
        self.assertFalse((self.root/'translations/gallery-text.ko.json').exists())


if __name__=='__main__': unittest.main(verbosity=2)
