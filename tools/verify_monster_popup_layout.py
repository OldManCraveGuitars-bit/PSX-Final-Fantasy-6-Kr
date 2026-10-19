"""Compare editor widths/sequence with measured real native AI pause points."""
import json, sys
from text_manager_model import Store, Metrics, audit
from textcodec import ROOT


def main():
    tag=sys.argv[1] if len(sys.argv)>1 else 'v071'
    native=json.loads((ROOT/'analysis'/f'{tag}-long-battle-native-verification.json').read_text('utf8'))
    insertion=json.loads((ROOT/'analysis/battle-big-text-insertion.json').read_text('utf8'))
    store=Store(ROOT)
    metrics=Metrics(json.loads((ROOT/'assets/text-manager/text-metrics.json').read_text('utf8')))
    metrics.refresh_variables(store.records)
    records={r.meta['index']:r for r in store.records if r.category=='monster_dialogue'}
    assert len(records)==256
    comparisons=[]
    for scenario in native['scenarios']:
        record=records[scenario['index']]
        stream=insertion['encoded'][scenario['record']]
        assert stream['translation']==record.text
        encoded=bytes.fromhex(stream['hex'])
        physical_line={}; line=1; p=0
        while encoded[p]:
            physical_line[p]=line
            c=encoded[p]
            if c==1:line+=1
            elif 0x1c<=c<=0x1f:p+=1
            p+=1
        _,_,lines=metrics.check(record)
        for pause in scenario['lines']:
            line_index=physical_line[pause['pointer_offset']]-1
            measured=pause['width_pixels']
            assert lines[line_index].width==measured,(record.uid,line_index,measured,lines[line_index].width)
            assert lines[line_index].number==1 and lines[line_index].page==line_index+1
            comparisons.append(dict(index=scenario['index'],screen=line_index+1,width=measured))
    rows=[r for r in audit(store,metrics) if store.by_uid[r['uid']].category=='monster_dialogue']
    errors=[(r['uid'],i) for r in rows for i in r['issues'] if i['severity']=='오류']
    assert not errors,errors
    result=dict(monster_records=len(records),native_pause_width_comparisons=comparisons,
                glyph_pixels=12,space_pixels=6,sequential_one_line_screens=True,
                automatic_wrap_rejected=True,hard_errors=0,
                source_native_verification=f'analysis/{tag}-long-battle-native-verification.json')
    (ROOT/'analysis/monster-popup-layout-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n','utf8')
    print(dict(monster_records=len(records),measured_native_width_cases=len(comparisons),hard_errors=0))


if __name__=='__main__':main()
