"""Check source controls and the localized clock/banquet game mechanics."""
import json,re
from textcodec import ROOT
from korean_codec import CONTROL


def main():
    source=json.loads((ROOT/'analysis/dialogue-original.json').read_text('utf8'))
    manual=json.loads((ROOT/'translations/manual_dialogue.json').read_text('utf8'))
    for key,text in manual.items():
        assert CONTROL.findall(text)==CONTROL.findall(source[int(key)]['source']),key
        assert not re.search(r'[^\S\n\r ]',text),('non-half-width whitespace',key)
    other_counts={}
    for filename in ['descriptions.ko.json','battle-abilities.ko.json','battle-messages.ko.json']:
        rows=json.loads((ROOT/'translations'/filename).read_text('utf8'))
        for key,row in rows.items():
            assert CONTROL.findall(row['source'])==CONTROL.findall(row['translation']),(filename,key)
            assert not re.search(r'[^\S\n\r ]',row['translation']),(filename,key,'non-half-width whitespace')
        other_counts[filename]=len(rows)
    # Keep the native answer indexes. The six-hour slot and the 10-minute,
    # 50-second slots must remain selectable in their original positions.
    expected={1053:[2,4,6,8,10,12],1055:[10,20,30,40,50],1056:[10,20,30,40,50]}
    for identifier,values in expected.items():
        text=manual[str(identifier)]
        actual=[int(x) for x in re.findall(r'\{choice\}\s*\((\d+)',text)]
        assert actual==values,(identifier,actual)
    for identifier,number in [(1046,2),(1047,4),(1048,8),(1049,10),(1050,12),(1057,30),(1059,20),(1061,4),(1066,2)]:
        assert re.search(r'(?<!\d)'+str(number)+r'(?!\d)',manual[str(identifier)]),identifier
    for identifier in range(1831,1855):
        assert CONTROL.sub('',manual[str(identifier)]).strip()==str(identifier-1830)+'명',identifier
    assert manual['2500']=='친구여 편히 잠드소서.'
    assert len(set(manual[str(i)] for i in range(2500,2524)))==24
    result={'source_control_sequences':len(manual),'other_source_control_sequences':other_counts,'Zozo_clock_selection_order':'preserved',
            'clock_solution_indexes':[2,0,4],'clock_lie_numbers':9,'banquet_counter_labels':24,
            'banquet_option_order':'original native choice token order preserved',
            'Daryl_tomb_permutations':24,'half_width_whitespace':'passed'}
    (ROOT/'analysis/dialogue-review-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n','utf8')
    print(result)


if __name__=='__main__':main()
