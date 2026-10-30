"""Audit every built field dialogue page, not just the reported opening."""
import json,re
from textcodec import ROOT
from dialogue_layout import timed_page_overflows,TIMED_CONTROL,PAGE_BOUNDARY

def scan(rows):
    timed=[];overflow=[]
    for index,row in enumerate(rows):
        ident=row.get('id',index)
        for page,text in enumerate(PAGE_BOUNDARY.split(row['translation']),1):
            if TIMED_CONTROL.search(text):
                timed.append({'id':ident,'page':page,'lines':text.count('\n')+1,'timers':TIMED_CONTROL.findall(text)})
        overflow.extend({'id':ident,**issue} for issue in timed_page_overflows(row['translation']))
    return {'records':len(rows),'timed_records':len({x['id'] for x in timed}),
            'timed_segments':len(timed),'overflow':overflow,'timed_pages':timed}

def main():
    snap=ROOT/'work/snapshots/v087-before-autodialogue-fix'
    before=scan(json.loads((snap/'analysis/dialogue-native-layout.json').read_text('utf8')))
    after=scan(json.loads((ROOT/'analysis/dialogue-native-layout.json').read_text('utf8')))
    assert before['records']==after['records']==3100
    assert {x['id'] for x in before['overflow']}=={3,459},before['overflow']
    assert after['overflow']==[],after['overflow']
    old=json.loads((snap/'translations/manual_dialogue.json').read_text('utf8'))
    new=json.loads((ROOT/'translations/manual_dialogue.json').read_text('utf8'))
    changed=[int(k) for k,v in new.items() if v!=old[k]]
    assert changed==[3,459],changed
    controls=re.compile(r'\{[^{}]+\}')
    assert all(controls.findall(new[k])==controls.findall(old[k]) for k in old)
    result={'scope':'All 3,084 main and 16 auxiliary built field messages; timed page controls after native pixel wrapping.',
        'baseline':before,'candidate':after,'changed_dialogue_ids':changed,
        'all_original_control_sequences_preserved':True,'font_pixels':12,'halfspace_pixels':6,
        'ordinary_button_scrolling_not_rejected':True,'full_story_playthrough':False}
    (ROOT/'analysis/v088-timed-dialogue-audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n','utf8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('baseline','candidate')},ensure_ascii=False))
    print('Timed segments:',after['timed_segments'],'remaining overflow:',len(after['overflow']))

if __name__=='__main__':main()
