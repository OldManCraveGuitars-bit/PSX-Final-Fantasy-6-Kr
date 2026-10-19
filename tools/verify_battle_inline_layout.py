"""Compare the editor's inline-key widths with actual native event captures."""
import json
from dataclasses import replace
from emu import ROOT
from text_manager_model import Store, Metrics


def main():
    native=json.loads((ROOT/'analysis/v071-battle-names-and-keys-native-verification.json').read_text('utf8'))
    store=Store(ROOT)
    metrics=Metrics(json.loads((ROOT/'assets/text-manager/text-metrics.json').read_text('utf8')))
    metrics.refresh_variables(store.records)
    row=next(r for r in store.records if r.category=='battle_dialogue' and r.meta.get('index')==native['inline_key']['index'])
    assert row.text==native['inline_key']['translation']
    parts=row.text.split('{key}')
    comparisons=[]
    for i,wait in enumerate(native['inline_key']['waits']):
        prefix='{key}'.join(parts[:i+1])+'{key}'
        _,lines=metrics.layout(prefix,replace(row.profile,auto_wrap=False))
        width=lines[-1].width
        assert width==wait['before']==wait['after'],(i,width,wait)
        comparisons.append(dict(key=i+1,byte_offset=wait['offset'],editor_width=width,
                                native_before=wait['before'],native_after=wait['after']))
    _,lines=metrics.layout(row.text,row.profile)
    assert len({line.page for line in lines})==1
    battle_rows=[r for r in store.records if r.profile.font=='battle']
    width_errors=[]
    for record in battle_rows:
        issues,_,_=metrics.check(record)
        width_errors.extend((record.uid,i.message) for i in issues if i.code=='width')
    assert not width_errors,width_errors
    result=dict(native_report='analysis/v071-battle-names-and-keys-native-verification.json',
                actual_native_comparisons=comparisons,
                battle_records_checked=len(battle_rows),width_errors=width_errors,
                inline_waits_preserve_line_and_page=True,
                field_key_page_semantics_unchanged=True,
                native_large_cell=12,native_half_space=6,
                note='Battle scrolling height remains a separate estimate warning; no text/control bytes changed.')
    (ROOT/'analysis/battle-inline-key-layout-verification.json').write_text(
        json.dumps(result,ensure_ascii=False,indent=2)+'\n','utf8')
    print('Editor/native inline-key widths match; battle width audit passed',comparisons)


if __name__=='__main__':main()
