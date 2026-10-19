"""Compare authored UI payloads and the original raw movie extents."""
import hashlib,json,sys
from pathlib import Path
from cdimage import directory_records
from textcodec import ROOT


def main():
    name=sys.argv[1];previous=sys.argv[2]
    base=ROOT/'work/candidates'/name;old=ROOT/'work/candidates'/previous
    report=json.loads((base/'build-report.json').read_text('utf8'))
    inventory=json.loads((ROOT/'analysis/disc_inventory.json').read_text('utf8'))
    sha=lambda b:hashlib.sha256(b).hexdigest()
    def payloads(path):
        with path.open('rb') as f:
            records=directory_records(f);out={}
            for rel in report['changed_files']:
                _,_,lba,size=records[rel];raw=bytearray()
                for i in range((size+2047)//2048):
                    f.seek((lba+i)*2352+24);raw+=f.read(2048)
                out[rel]=bytes(raw[:size])
            return out,records
    now,records=payloads(base/(name+'.bin'));prior,_=payloads(old/(previous+'.bin'))
    changed=[rel for rel in now if now[rel]!=prior[rel]]
    expected=set(sys.argv[3:]) if len(sys.argv)>3 else {'HAR/MENUMENU.BIN','HAR/HARATA.PAC','DEODIR/ALLTIM.BIN'}
    assert set(changed)==expected,changed
    movies={}
    with (base/(name+'.bin')).open('rb') as target,Path(inventory['source']['track_path']).open('rb') as source:
        for rel in ['MOVIE/OPEN.STR','MOVIE/OPERA.STR','MOVIE/END.STR']:
            _,_,lba,size=records[rel];count=(size+2047)//2048
            target.seek(lba*2352);source.seek(lba*2352)
            a=target.read(count*2352);b=source.read(count*2352)
            assert a==b,rel
            movies[rel]={'raw_sectors_byte_identical':True,'raw_extent_sha256':sha(a),'sectors':count}
    from text_manager_model import Store
    store=Store(ROOT)
    result={'candidate':name,'compared_with':previous,'changed_payloads':changed,
        'authored_resources':{rel:{'sha256':sha(data),'unchanged_from_previous':data==prior[rel]} for rel,data in now.items()},
        'original_movie_extents':movies,'registered_records':len(store.records),'reviewed_records':sum(r.reviewed for r in store.records),
        'text_manager_sha256':sha((ROOT/'FF6KoreanTextManager.exe').read_bytes())}
    version=name.rsplit('-',1)[-1]
    (ROOT/'analysis'/f'{version}-resource-regression.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n','utf8')
    print({'changed_payloads':changed,'other_payloads_unchanged':True,'original_raw_movies':'byte-identical'})


if __name__=='__main__':main()
