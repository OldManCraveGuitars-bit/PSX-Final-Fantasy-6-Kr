"""Keep the native tomb inscription puzzle solvable in Korean."""
import json,re
from textcodec import ROOT
from korean_codec import CONTROL

WORDS={'とも':'친구여','よや':'편히','すら':'잠드','かに':'소서'}

def main():
    source=json.loads((ROOT/'analysis/dialogue-original.json').read_text('utf8'))
    p=ROOT/'translations/manual_dialogue.json';manual=json.loads(p.read_text('utf8'));updates={}
    for i in range(2483,2500):
        text=source[i]['source']
        for jp,ko in WORDS.items():text=text.replace(jp,ko)
        updates[str(i)]=text
    inscriptions=[]
    for i in range(2500,2524):
        jp=re.sub(r'\s','',source[i]['source'])
        pieces=[jp[j:j+2] for j in range(0,len(jp),2)]
        assert len(pieces)==4 and set(pieces)==set(WORDS),i
        ko=' '.join(WORDS[x] for x in pieces).replace('잠드 소서','잠드소서')
        if i==2500:ko+='.'
        updates[str(i)]=ko;inscriptions.append(ko)
    updates['2524']='묘비에는 아무것도 적혀 있지 않다.\n글자를 새기겠습니까?\n{choice} 예\n{choice} 아니요'
    updates['2525']='좋은 문구가 떠오르지 않는다…'
    updates['2526']='글자가 새겨져 있다…'
    for i in range(2527,2531):
        text=source[i]['source']
        for jp,ko in WORDS.items():text=text.replace(jp,ko)
        updates[str(i)]=text
    updates['2531']='지하 3층 안쪽 방에\n그로우에그를 숨겨 두었다…'
    updates={k:v.replace('\u3000',' ') for k,v in updates.items()}
    for k,v in updates.items():assert CONTROL.findall(v)==CONTROL.findall(source[int(k)]['source']),k
    assert len(set(inscriptions))==24
    assert updates['2500']=='친구여 편히 잠드소서.'
    manual.update(updates)
    p.write_text(json.dumps(manual,ensure_ascii=False,indent=2)+'\n','utf8')
    (ROOT/'analysis/daryl-tomb-localization.json').write_text(json.dumps({'reviewed_records':len(updates),
        'native_selection_order':'preserved','permutations':24,'correct_inscription':updates['2500'],
        'word_pieces':WORDS,'source_control_sequences':'preserved'},ensure_ascii=False,indent=2)+'\n','utf8')
    print('Localized',len(updates),'native inscription/choice records; all 24 permutations checked')

if __name__=='__main__':main()
