"""Freeze the completed language-review result without editing source prose."""
import collections, hashlib, json
from textcodec import ROOT
from text_manager_model import Store, CONTROL

def main():
    folder=ROOT/'work/proofreading-v072'
    before=json.loads((folder/'before.json').read_text('utf8'))
    store=Store(ROOT)
    old={r['uid']:r for r in before}
    planned={r['uid'] for r in json.loads((folder/'batch.json').read_text('utf8'))}
    changed=[]
    for row in store.records:
        if row.uid not in old:continue
        original=old[row.uid]
        assert row.source==original['source'] and row.reviewed==original['reviewed'],row.uid
        assert CONTROL.findall(row.text)==CONTROL.findall(original['translation']),row.uid
        if row.text!=original['translation']:changed.append(row)
    assert len(old)==7655 and len(changed)==264
    assert {r.uid for r in changed}==planned
    audit=json.loads((ROOT/'analysis/proofreading-v072-audit.json').read_text('utf8'))
    assert not [i for r in audit for i in r['issues'] if i['severity']=='오류']
    warnings=collections.Counter(i['code'] for r in audit for i in r['issues'] if i['severity']=='주의')
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    report=dict(records=7655,changed_records=len(changed),by_group=dict(collections.Counter(r.group for r in changed)),
        source_controls_and_review_flags_preserved=True,unplanned_text_changes=0,hard_layout_errors=0,
        warning_counts=dict(warnings),import_reports=['analysis/proofreading-v072-import.json','analysis/proofreading-v072-capacity-fix.json'],
        source_prose_sha256_after_import={p.relative_to(ROOT).as_posix():sha(p) for p in (ROOT/'translations').glob('*.json')},
        text_manager_version='1.10',model_tests=38,standalone_widgets='analysis/text-manager-v110-widget-test.json',
        native_render='analysis/v072-dialogue-native-verification.json',
        candidate_image='analysis/v072-image-verification.json',
        scope=json.loads((folder/'coverage.json').read_text('utf8'))['scope'])
    (ROOT/'analysis/proofreading-v072-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8')
    final=[dict(uid=r.uid,source=r.source,translation=r.text,reviewed=r.reviewed) for r in changed]
    (folder/'applied-final.json').write_text(json.dumps(final,ensure_ascii=False,indent=2)+'\n','utf8')
    print({k:v for k,v in report.items() if k not in ['source_prose_sha256_after_import','scope']})
if __name__=='__main__':main()
