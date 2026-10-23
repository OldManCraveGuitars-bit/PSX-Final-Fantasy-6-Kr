"""Explicit proofreading edits and conservative line reflow for the v086 review.

This stages a text-manager import, never edits the canonical translation files.
Reviewed ranges are recorded separately; a formatting pass is not a prose review.
"""
import json,re
from dataclasses import asdict,replace
from pathlib import Path
from textcodec import ROOT
from korean_codec import CONTROL
from text_manager_model import Store,Metrics,load_json

FIELD_EDITS = {
    61: '{hchar00}「으...\n아무것도 뚜렷이 떠오르지 않아.\n그전 일도... 아주 옛날 일도...',
    250: '{hchar01}「아까부터\n어슬렁거리던 게 너였구나?\n바르가스「알 게 뭐냐!',
    428: '{hchar04}「여기는...\n{hchar00}「왜?{page}{hchar04}「나르셰의 경비병이 되려는\n실력자들이 시험을 치르는 곳이\n있다고 들었어. 분명...\n저 빛을 따라가면 무사히\n도착할 수 있을 거야. 길을 틀리면\n빛에 둘러싸이는데, 그때는\n붉은빛을 골라야 앞으로 갈 수 있어...',
    474: '크, 큰일 났어요.\n단장님께 가 주세요.',
    606: '장신구가 뭔지 알고 있나요?',
    630: '「리플렉」에 관한 설명입니다.\n한 번 리플렉으로 반사된 마법은\n다시 리플렉으로 반사할 수 없습니다.{page}이것을 응용한 공격법도 있습니다.\n아군에게 리플렉을 건 뒤,\n그 동료에게 공격 마법을 쓰는 것이지요.\n이해되나요?',
    763: '제국 병사들이 마란다 거리를 다녀서\n전보다 삼엄해졌지만,\n그 밖에는 평온한 하루하루를\n보내고 있어요.{page}정원의 꽃이 막 피어나기 시작했어요.\n이제 봄이 오나 봐요.{page}몸은 좀 어떠세요?\n마음 같아서는 당장 당신께\n달려가고 싶어요... 걱정돼 견딜 수 없어요.\n지금은 몸을 회복할 생각만 하세요.{page}절대 무리하지 마세요.\n매일 당신만 생각하고 있어요.\n어서 만나고 싶어요...\n{t[0F]}로라',
    1200: '{hchar06}「난... 그 사람의 대역이야?',
    1246: '{hchar01}「세계 최고의 트레저 헌터!\n바로 이 {char01} 님이시다아!',
    1405: '시드「환수의 생명으로\n힘을 얻다니...',
    1466: '가스트라「하하! 드디어 찾아냈다!{page}천 년 전 문헌의 수수께끼를 풀어\n마도의 비밀과 환수계의 입구를\n찾아낸 노력이 드디어 결실을 맺었구나.',
    2162: '『이 아래에 비공정이 있어.\n{choice}(뛰어내린다)\n{choice}(기다린다)',
    2742: '『배, 백만 길!?',
    2951: '\n{gp}길이 들어 있었다!',
}

# Actual read-through coverage, expanded only after reviewing the displayed text.
FIELD_REVIEWED_RANGES = [[0,3083]]

def reflow(text):
    """Join only prose continuation lines; preserve events, lists and lyrics."""
    if any(t in text for t in ('{t[','{choice}','♬','♪','♫')):
        return text
    lines=text.split('\n');out=[lines[0]]
    for line in lines[1:]:
        previous=out[-1].rstrip();current=line.strip()
        boundary=(not previous or not current or
            re.search(r'[.!?…:。！？」』]$',previous) or
            previous.endswith('}') or current.startswith('{') or
            re.match(r'[^\s「『]{0,12}[「『]',current) or
            re.match(r'(?:[0-9]+[.)]|[「『・※＊*]|[가-힣]+\.\.\.)',current))
        if boundary:out.append(line.rstrip())
        else:out[-1]=previous+' '+current
    return '\n'.join(out)

def stage():
    store=Store(ROOT);metrics=Metrics(load_json(ROOT/'assets/text-manager/text-metrics.json'))
    metrics.refresh_variables(store.records)
    batch=[];log=[];reviewed={}
    for r in store.records:
        if r.group not in ('대사','PSX 도움말','전투 문장','전투 기술·대사'):continue
        reviewed[r.group]=reviewed.get(r.group,0)+1
        text=r.text;p=replace(r.profile)
        if r.group=='대사':
            text=FIELD_EDITS.get(int(r.key),text)
            text=text.replace('대삼각섬로','대삼각섬으로').replace('도구을','도구를').replace('도구은','도구는')
            text=text.replace('액세서리','장신구').replace('{char08}랑','{char08}이랑')
            # Deliberately scrambled gravestone phrases are a native puzzle.
            if not (6<=int(r.key)<=9 or 1189<=int(r.key)<=1235 or 2483<=int(r.key)<=2530):text=reflow(text)
        if r.group in ('대사','PSX 도움말'):
            for a,b in [('A 버튼','결정 버튼'),('B 버튼','취소 버튼'),('X나 Y 버튼','메뉴나 파티 버튼'),('X 버튼','메뉴 버튼'),('Y 버튼','파티 버튼')]:
                text=text.replace(a,b)
            if r.group=='PSX 도움말':text=reflow(text)
            text=metrics.wrap(text,p,safe=True)
        if r.group=='전투 문장' and r.category=='battle_dialogue':
            text=text.replace('A 버튼','결정 버튼')
            if int(r.key) in (30,84,86):text=text.replace('왼쪽{key}, 오른쪽{key}, 왼쪽{key}, A다!{key}','왼쪽{key}, 오른쪽{key}, 왼쪽{key},\n결정 버튼이다!{key}')
            if int(r.key)==214:text='3. 왼쪽, 오른쪽, 왼쪽 순서로\n방향키를 누릅니다.{key}'
            # Reserve one large cell at the right edge of this native box.
            p=replace(p,width=204,auto_wrap=False,note='전투 대사 12px 글꼴, 공백 6px. 오른쪽 테두리 여유 12px을 남겨 204px로 검사. 대기 코드는 유지합니다.')
            text=metrics.wrap(text,p,safe=True)
        if tuple(CONTROL.findall(text))!=r.baseline_controls:raise ValueError(('controls',r.uid,text,r.text))
        issues,_,lines=metrics.check(r,text,p)
        errors=[asdict(i) for i in issues if i.severity=='오류']
        if errors:raise ValueError((r.uid,errors))
        if text!=r.text or p!=r.profile:
            batch.append(dict(uid=r.uid,translation=text,reviewed=True,profile=asdict(p)))
            log.append(dict(uid=r.uid,before=r.text,after=text,old_width=r.profile.width,width=p.width))
    save(ROOT/'analysis/v086-proofread-batch.json',batch)
    save(ROOT/'analysis/v086-proofread-changes.json',log)
    return reviewed,len(batch)

def save(path,value):
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n','utf8')

if __name__=='__main__':
    reviewed,changed=stage()
    save(ROOT/'analysis/v086-review-progress.json',{
        'field_read_through_ranges':FIELD_REVIEWED_RANGES,
        'read_through_complete':True,'build_and_native_verification_complete':False,
        'reviewed_records':reviewed,'staged_entries':changed,
        'scope':'Korean prose, context, particles, terminology and line continuity; Japanese consulted for ambiguous passages.',
        'explicit_field_edits':FIELD_EDITS})
