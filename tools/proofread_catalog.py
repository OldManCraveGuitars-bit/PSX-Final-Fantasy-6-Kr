"""Read-only catalog snapshots and review batches for the standalone editor.

Canonical prose is never written here. Approved corrections are imported by
FF6KoreanTextManager.exe, with its backup/control/layout validation.
"""
import argparse, hashlib, json, re
from pathlib import Path
from text_manager_model import Store, CONTROL, normalized

ROOT=Path(__file__).resolve().parents[1]
FOLDER=ROOT/'work/proofreading-v072'


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--snapshot',action='store_true')
    parser.add_argument('--group',default='대사')
    parser.add_argument('--start',type=int,default=0)
    parser.add_argument('--count',type=int,default=200)
    parser.add_argument('--source',action='store_true')
    parser.add_argument('--unique',action='store_true')
    args=parser.parse_args()
    store=Store(ROOT)
    if args.snapshot:
        FOLDER.mkdir(parents=True,exist_ok=True)
        rows=[dict(uid=r.uid,group=r.group,key=r.key,category=r.category,source=r.source,
                   translation=r.text,reviewed=r.reviewed) for r in store.records]
        path=FOLDER/'before.json'
        if path.exists():raise ValueError('A proofreading baseline already exists; preserve it.')
        path.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n','utf8')
        hashes={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
                for p in (ROOT/'translations').glob('*.json')}
        (FOLDER/'before-sha256.json').write_text(json.dumps(hashes,indent=2)+'\n','utf8')
        print('Snapshot',len(rows),'records')
    rows=[r for r in store.records if r.group==args.group]
    seen=set()
    for r in rows[args.start:args.start+args.count]:
        identity=(r.source,r.text) if args.source else r.text
        if args.unique and identity in seen:continue
        seen.add(identity)
        text=r.text.replace('\n',' / ')
        # Speaker IDs remain visible; nonprinting timing bytes are omitted.
        text=re.sub(r'\{(?:pause|key|wait)(?:\[[^]]*\])?\}','',text)
        text=text.replace('{page}',' // ')
        text=re.sub(r'\{t\[[^]]+\]\}','',text)
        if args.source:print(r.key,r.source.replace('\n',' / '),'=>',text)
        else:print(r.key,text)


if __name__=='__main__':main()
