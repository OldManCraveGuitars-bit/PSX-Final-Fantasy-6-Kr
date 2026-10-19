"""Prepare reviewed prose corrections, without writing canonical translations."""
import json,re
from collections import Counter
from dataclasses import replace
from proofread_catalog import ROOT,FOLDER
from text_manager_model import Store,Metrics,CONTROL

TERMS=[
 ('아머카파','임프 아머'),('뷔스체','뷔스티에'),
 ('드라쿠','드라코'),('대릴','다릴'),('세리스','셀리스'),
 ('코링겐','콜린겐'),('다달루마','다달마'),
 ('훔바바','푼바바'),('티폰','튜폰'),('알렉 소울','알렉소울'),
 ('에레보스','엘레보스'),('리플레크','리플렉'),
 ('갓파','임프'),('캇파','임프'),('카파','임프'),
 ('짐승의 들판','짐승의 평원'),('초승달산','초승달 산'),('조조산','조조 산'),
 ('대삼각도','대삼각섬'),('피가로성','피가로 성'),('도마성','도마 성'),('제국성','제국 성'),
 ('보물상자','보물 상자'),('데스게이즈','데스 게이즈'),('에어포스','에어 포스'),
 ('디그아머','디그 아머'),('프로토아머','프로토 아머'),('마도아머','마도 아머'),
 ('보물 사냥꾼이라고','트레저 헌터라고'),('보물 사냥꾼이라는','트레저 헌터라는'),
 ('보물 사냥꾼이라도','트레저 헌터라도'),('보물 사냥꾼이야','트레저 헌터야'),
 ('보물 사냥꾼','트레저 헌터'),('웨이트','대기'),
 ('하이 포션','하이포션'),('에테르 터보','터보에테르'),('피닉스의 꼬리','불사조의 꼬리'),
 ('대시 슈즈','대시슈즈'),('용기사의 신발','용기사 신발'),
 ('바이오블라스트','바이오블래스트'),('마음없는 천사','마음 없는 천사'),
 ('임시파일','임시 파일'),('붉은 빛','붉은빛'),('아이템','도구'),
]
PAIRS={'은':'는','이':'가','을':'를','과':'와','이다':'다','이라는':'라는','이라고':'라고','이죠':'죠'}


def ending(word,particle):
    if not word or not '가'<=word[-1]<='힣':return particle
    jong=(ord(word[-1])-0xac00)%28
    if particle in ('으로','로'):return '로' if jong in (0,8) else '으로'
    return next((a if jong else b for a,b in PAIRS.items() if particle in (a,b)),particle)


def main():
    store=Store(ROOT)
    baseline=json.loads((FOLDER/'before.json').read_text('utf8'))
    by_location={(r['group'],r['key']):r for r in baseline}
    decisions=json.loads((FOLDER/'decisions.json').read_text('utf8'))
    explicit={}
    for d in decisions:explicit.setdefault((d['group'],d['key']),[]).append(d)
    names={int(r.key):r.text for r in store.records if r.group=='이름·도구·마법' and r.category=='character'}
    char_pattern=re.compile(r'\{h?char(?:\[([0-9A-Fa-f]{2})\]|(\d+))\}(으로|로|이라는|라고|이라고|라는|이다|이죠|죠|은|는|이|가|을|를|과|와|다)(?=[^가-힣]|$)')
    quote_pattern=re.compile(r'([가-힣])([」』”\'\"])(으로|로|은|는|이|가|을|를|과|와)(?=[^가-힣]|$)')
    plans=[];batch=[]
    for r in store.records:
        original=by_location[(r.group,r.key)]
        text=original['translation'];reasons=[]
        assert r.text==text,'Source changed during proofreading: '+r.uid
        for d in explicit.get((r.group,r.key),[]):
            assert d['old'] in text,(r.uid,d['old'])
            text=text.replace(d['old'],d['new']);reasons.append(d['reason'])
        for old,new in TERMS:
            if old in text:
                text=text.replace(old,new);reasons.append('문맥 및 등록 용어 통일: '+old+' → '+new)
        if r.group in ('대사','설명문','전투 기술·대사','전투 문장','부록 문장','PSX 도움말'):
            changed=re.sub(r'(?<![\d,])([1-9]\d{3,})(?=길)',lambda m:format(int(m[1]),','),text)
            if changed!=text:reasons.append('금액 자릿수 표기 통일; 원래 수치는 유지');text=changed
        if r.group in ('대사','전투 문장','전투 기술·대사','PSX 도움말'):
            def fix_char(m):
                idx=int(m[1],16) if m[1] is not None else int(m[2])
                desired=ending(names.get(idx,''),m[3])
                if desired!=m[3]:reasons.append('기본 이름 '+names[idx]+' 뒤 조사: '+m[3]+' → '+desired)
                return m[0][:-len(m[3])]+desired
            text=char_pattern.sub(fix_char,text)
        def fix_quote(m):
            desired=ending(m[1],m[3])
            if desired!=m[3]:reasons.append('따옴표 안의 명칭 뒤 조사: '+m[3]+' → '+desired)
            return m[1]+m[2]+desired
        text=quote_pattern.sub(fix_quote,text)
        if text==r.text:continue
        assert CONTROL.findall(text)==CONTROL.findall(r.text),r.uid
        assert re.findall(r'\d+',CONTROL.sub('',text).replace(',',''))==re.findall(r'\d+',CONTROL.sub('',r.text).replace(',','')),('Changed numeric value',r.uid)
        plans.append(dict(uid=r.uid,group=r.group,id=r.key,before=r.text,after=text,reasons=list(dict.fromkeys(reasons))))
        batch.append(dict(uid=r.uid,source=r.source,translation=text,reviewed=r.reviewed))
    metrics=Metrics(json.loads((ROOT/'assets/text-manager/text-metrics.json').read_text('utf8')))
    metrics.refresh_variables(store.records,{r['uid']:r['translation'] for r in batch})
    issues=[]
    for row in batch:
        record=store.by_uid[row['uid']]
        found,effective,_=metrics.check(record,row['translation'])
        for issue in found:
            if issue.severity=='오류':issues.append(dict(uid=row['uid'],code=issue.code,message=issue.message))
        row['translation']=effective if record.profile.auto_wrap else row['translation']
    # Catalog renames can change variable reservations in untouched messages.
    overrides={r['uid']:r['translation'] for r in batch}
    for record in store.records:
        if record.uid in overrides:continue
        found,_,_=metrics.check(record)
        issues.extend(dict(uid=record.uid,code=i.code,message=i.message) for i in found if i.severity=='오류')
    (FOLDER/'batch.json').write_text(json.dumps(batch,ensure_ascii=False,indent=2)+'\n','utf8')
    (FOLDER/'changes.json').write_text(json.dumps(plans,ensure_ascii=False,indent=2)+'\n','utf8')
    (FOLDER/'preflight-errors.json').write_text(json.dumps(issues,ensure_ascii=False,indent=2)+'\n','utf8')
    coverage=dict(records=len(baseline),groups=dict(Counter(r['group'] for r in baseline)),
        scope='All registered Korean text read for context, spelling, particles, spacing, terminology and punctuation; identical repeated/empty entries checked together. Ambiguous meanings checked against the supplied Japanese source. This does not claim a complete story playthrough or decipher the remaining illegible art note.',
        proposed_changed_records=len(batch),by_group=dict(Counter(r['group'] for r in plans)),
        source_controls_and_numbers_preserved=True,preflight_hard_errors=issues,
        editable_source='Standalone FF6KoreanTextManager.exe batch import only; this preparer writes work files only.',
        intentional_exceptions=['Gau/Ultros/Moogle speech, drunk/deliberately broken speech and ellipses retained.',
            'Clock/banquet answers and Daryl tomb permutations retained.',
            'Native positioned numeric insertion spaces retained.',
            'Actor particles follow the catalog default names; arbitrary player renames need runtime particle selection to guarantee the same grammar.'])
    (FOLDER/'coverage.json').write_text(json.dumps(coverage,ensure_ascii=False,indent=2)+'\n','utf8')
    print(json.dumps(dict(changed=len(batch),by_group=coverage['by_group'],hard_errors=issues),ensure_ascii=False))


if __name__=='__main__':main()
