"""Consolidate complete dialogue drafts and verify all original engine controls."""
import json,re,collections
from textcodec import ROOT
from korean_codec import normalize,CONTROL
def clean(text):
    text=normalize(text)
    text='\n'.join(re.sub(' +',' ',line).strip() for line in text.splitlines())
    text=re.sub(r'\n{2,}','\n',text)
    text=re.sub(r'\n*(\{(?:page|key(?:\[[^]]+\])?)\})\n*',r'\1',text)
    return text.strip()
def main():
    src=json.loads((ROOT/'analysis/dialogue-original.json').read_text('utf-8'))
    draft=json.loads((ROOT/'translations/dialogue.ko.json').read_text('utf-8'))
    manual=json.loads((ROOT/'translations/manual_dialogue.json').read_text('utf-8'))
    rows=[];errors=[]
    for row in src:
        k=str(row['id']);ko=manual[k] if k in manual else draft[k]['translation']
        if CONTROL.findall(row['source'])!=CONTROL.findall(ko):errors.append({'id':row['id'],'error':'Control sequence mismatch','source':CONTROL.findall(row['source']),'translation':CONTROL.findall(ko)})
        if re.search('[\u3041-\u3096\u30a1-\u30fa\u3400-\u9fff\uff66-\uff9d]',ko):errors.append({'id':row['id'],'error':'Japanese residual'})
        rows.append(dict(**row,translation=clean(ko),status='manual' if k in manual else 'machine_draft'))
    report={'entries':len(rows),'manually_translated':sum(x['status']=='manual' for x in rows),'machine_draft':sum(x['status']=='machine_draft' for x in rows),'errors':errors,'insertion_complete':False,'menus_complete':False,'all_text_localized':False}
    (ROOT/'translations/dialogue.complete-draft.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n','utf-8')
    (ROOT/'analysis/dialogue-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf-8')
    print(json.dumps(report,ensure_ascii=False))
    if errors:raise ValueError('Dialogue control/source validation failed')
if __name__=='__main__':main()
