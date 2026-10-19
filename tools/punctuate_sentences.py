"""Add terminal periods to Korean sentences, preserving names and controls."""
import json,re,sys,os,shutil
from functools import lru_cache
from textcodec import ROOT
from korean_codec import CONTROL,normalize

FILES=['manual_dialogue.json','dialogue.ko.json','psx_auxiliary.json',
    'descriptions.ko.json','battle-abilities.ko.json','battle-messages.ko.json',
    'omake-manual.json','omake.ko.json','psx-ui-messages.ko.json']

def apply():
    try:from kiwipiepy import Kiwi
    except ImportError:
        # Reuse the installed offline Korean language tools on this workspace.
        site=os.environ.get('FF6_KIWI_SITE',str(ROOT.parent/'_tmp_kiwipiepy_successor244'))
        sys.path.insert(0,site)
        from kiwipiepy import Kiwi
    kiwi=Kiwi(num_workers=1)
    names=set()
    names.update(['가나','없음','필요 없음','예','아니오','아니요','뭔가','어딘가','누군가','언젠가'])
    for filename in ['fixed-catalog.ko.json','map-titles.json','menu-jobs.ko.json']:
        rows=json.loads((ROOT/'translations'/filename).read_text('utf8'))
        for row in rows.values() if isinstance(rows,dict) else rows:
            names.add(CONTROL.sub('',normalize(row['translation'])).strip())
    documents={name:json.loads((ROOT/'translations'/name).read_text('utf8')) for name in FILES}
    for rows in documents.values():
        texts=rows.values() if isinstance(rows,dict) else rows
        for row in texts:
            value=row if isinstance(row,str) else row['translation']
            for speaker in re.findall(r'(?:^|\n|\{page\})([^\n{}「]{1,24})「',value):names.add(speaker.strip())
    fixed=json.loads((ROOT/'translations/fixed-catalog.ko.json').read_text('utf8'))
    actors=[fixed[str(i)]['translation'] for i in range(64)]
    @lru_cache(maxsize=None)
    def punctuate(text):
        # Analyze the complete utterance. A line break alone never ends a
        # sentence: e.g. '부활시켜\n세상을 지배한다' retains the connective.
        chars=[];positions=[]
        # A menu option can wrap onto several physical lines. Protect the
        # whole option through the next choice or actual message boundary.
        choices=[(m.start(),m.end()) for m in re.finditer(r'\{choice\}.*?(?=\{(?:choice|page|key(?:\[[^]]+\])?)\}|$)',text,re.S)]
        for match in re.finditer(r'\{[^{}]+\}|[^{}]',text):
            part=match[0];at=match.start()
            if part.startswith('{'):
                actor=re.fullmatch(r'\{h?char(\d+)\}',part)
                replacement=actors[int(actor[1])%64] if actor else {'{item}':'포션','{spell}':'파이어','{gp}':'100','{page}':' '}.get(part,'')
                chars.extend(replacement);positions.extend([-1]*len(replacement))
            else:
                chars.append(' ' if part=='\n' else part);positions.append(at)
        plain=''.join(chars);insert=set()
        # Give only the end of the complete utterance sentence context. Never
        # append an artificial boundary to each physically wrapped line.
        tokens=kiwi.tokenize(plain+'.')
        for t in tokens:
            if t.tag!='EF' or t.form in ('음','ㅁ','ᆷ','기'):continue
            end=t.start+t.len
            if not end or end>len(positions) or positions[end-1]<0:continue
            at=positions[end-1]+1
            if any(a<=at<=b for a,b in choices):continue
            # An ending inside a word (e.g. a place name followed by a particle)
            # is never a sentence boundary.
            if at<len(text) and text[at] not in ' \n\t{」』”\"\'':continue
            tail=text[at:]
            # Timing/keypress controls can stand between the last word and an
            # existing exclamation, period or ellipsis.
            visible=re.sub(r'^(?:\s|\{(?:pause1?|pause\[[^]]+\]|key(?:\[[^]]+\])?|t\[[^]]+\])\}|[」』”\"\'♬])*','',tail)
            if visible[:1] and visible[0] in '.!?…。！？,:;～~ー-':continue
            # Require an actual message/page/speaker boundary. A physical
            # wrap, embedded quote, or vocative alone is not such a boundary.
            rest=re.sub(r'^(?:\s|\{(?:pause1?|pause\[[^]]+\]|key(?:\[[^]]+\])?|t\[[^]]+\])\}|[」』”\"\'♬])*','',tail)
            next_speaker=re.match(r'^(?:\s|\{[^{}]+\})*[^\n{}「]{0,24}「',tail)
            if rest and not rest.startswith('{page}') and not next_speaker:continue
            left=text.rfind('\n',0,at)+1
            line=CONTROL.sub('',text[left:at]).strip(' 「『“\"\'♬')
            if line in names:continue
            if line.split() and all(x in ('오','아','우','흠','허','호','하','음냐','케','가우') for x in line.split()):continue
            if re.search(r'(?:^|\s)피해$',line):continue
            insert.add(at)
        result=text
        for at in sorted(insert,reverse=True):result=result[:at]+'.'+result[at:]
        assert CONTROL.findall(result)==CONTROL.findall(text)
        return result
    assert punctuate('힘이 사라졌다')=='힘이 사라졌다.'
    assert punctuate('마대전')=='마대전'
    assert punctuate('세상에서')=='세상에서'
    assert punctuate('힘이 사라졌다{pause[FF]}{key}')=='힘이 사라졌다.{pause[FF]}{key}'
    assert punctuate('{choice} (다음에 온다)')=='{choice} (다음에 온다)'
    assert punctuate('{choice}『어느 쪽이든\n {char06}를 믿는다')=='{choice}『어느 쪽이든\n {char06}를 믿는다'
    assert punctuate('{choice} 돌아간다{page}힘이 사라졌다')=='{choice} 돌아간다{page}힘이 사라졌다.'
    assert punctuate('힘을 부활시켜\n세상을 지배한다')=='힘을 부활시켜\n세상을 지배한다.'
    assert punctuate('마법의 힘을 부활시켜\n세상을 지배하려는 자가 있다…')=='마법의 힘을 부활시켜\n세상을 지배하려는 자가 있다…'
    assert punctuate('{char06}에게\n납치되고 말았습니다.')=='{char06}에게\n납치되고 말았습니다.'
    assert punctuate('없음')=='없음'
    assert punctuate('나를 말하지 마{key}!{key}')=='나를 말하지 마{key}!{key}'
    assert punctuate('무슨 소린가{key}. 정말이야.')=='무슨 소린가{key}. 정말이야.'
    assert punctuate('「마석 라무」를 손에 넣었다.')=='「마석 라무」를 손에 넣었다.'
    assert punctuate('그대를 기다려요 ♬ {pause[1C]}{key}')=='그대를 기다려요. ♬ {pause[1C]}{key}'
    assert punctuate('메뉴로 돌아가')=='메뉴로 돌아가.'
    assert punctuate('1000 피해')=='1000 피해'
    assert punctuate('아니오')=='아니오'
    changes=[];counts={};backup=ROOT/'work/punctuation-before-v050';backup.mkdir(exist_ok=True)
    for filename,rows in documents.items():
        count=0
        items=list(rows.items()) if isinstance(rows,dict) else enumerate(rows)
        for key,row in items:
            if filename=='dialogue.ko.json' and str(key) in documents['manual_dialogue.json']:continue
            # These records are deliberately incomplete movable word pieces.
            if filename in ('manual_dialogue.json','dialogue.ko.json') and (2501<=int(key)<=2523 or 2527<=int(key)<=2530):continue
            old=row if isinstance(row,str) else row['translation'];new=punctuate(old)
            if new==old:continue
            changes.append({'file':filename,'id':key,'before':old,'after':new});count+=1
            if isinstance(row,str):rows[key]=new
            else:row['translation']=new
        counts[filename]=count
        if count:
            path=ROOT/'translations'/filename
            if not (backup/filename).exists():shutil.copyfile(path,backup/filename)
            path.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n','utf8')
    result={'changed_records':len(changes),'by_file':counts,'controls':'unchanged',
        'rule':'period after Korean final endings; names, titles, options and existing punctuation retained',
        'changes':changes}
    target=ROOT/'analysis/sentence-punctuation.json'
    # Retain the substantive audit when an idempotence check makes no changes.
    if changes or not target.exists():target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n','utf8')
    return {k:v for k,v in result.items() if k!='changes'}

if __name__=='__main__':print(json.dumps(apply(),ensure_ascii=False))
