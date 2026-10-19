"""Check authored ISO payloads, Mode-2 EDC/ECC and immutable source image."""
import json,sys
from cdimage import directory_records,protect,sha256
from textcodec import ROOT
from build_main_dialogue import CANDIDATE


def main():
    name=sys.argv[1] if len(sys.argv)>1 else CANDIDATE
    base=ROOT/'work/candidates'/name
    report=json.loads((base/'build-report.json').read_text('utf8'))
    payloads=ROOT/report.get('payload_directory',('work/v081-cache-payloads' if report.get('field_cache') else 'work/modified'))
    inv=json.loads((ROOT/'analysis/disc_inventory.json').read_text('utf8'))
    count=0
    with (base/(name+'.bin')).open('rb') as handle:
        records=directory_records(handle)
        for path in payloads.rglob('*'):
            if not path.is_file():continue
            rel=path.relative_to(payloads).as_posix()
            if rel not in records:continue
            _,_,lba,size=records[rel];out=bytearray()
            for i in range((size+2047)//2048):
                handle.seek((lba+i)*2352+24);out+=handle.read(2048)
            expected=path.read_bytes()
            if rel=='HAR/MENUMENU.BIN' and report.get('field_cache'):
                from lz4.block import decompress,compress
                assert bytes(out[:size])==(payloads/'menu-disc.bin').read_bytes()
                first,second=report['field_cache']['menu_part_bytes']
                used1=len(compress(expected[:0x33000],mode='high_compression',compression=12,store_size=True))
                used2=len(compress(expected[0x52000:0x60000],mode='high_compression',compression=12,store_size=True))
                assert decompress(bytes(out[:used1]))==expected[:0x33000]
                assert decompress(bytes(out[first:first+used2]))==expected[0x52000:0x60000]
                count+=1
                continue
            if rel=='HAR/MENUMENU.BIN' and report.get('menu_loading'):
                from lz4.block import decompress
                from small_runtime import MENU_READ_SIZE
                assert bytes(out[:size])==(ROOT/'work/menu-disc.pac').read_bytes()
                used=report['menu_loading']['compressed_bytes']
                assert decompress(bytes(out[:used]))==expected[:MENU_READ_SIZE]
                assert not any(expected[MENU_READ_SIZE:])
                count+=1
                continue
            assert bytes(out[:len(expected)])==expected,rel
            count+=1
        for lba in set(report['changed_lbas']):
            handle.seek(lba*2352);raw=handle.read(2352)
            assert protect(raw)==raw,lba
        field_report=report['field_cache']['full_reload'] if report.get('field_cache') else report.get('menu_loading',{}).get('field_return',{})
        if field_report.get('texture_mirror_lba'):
            expected=(ROOT/'work/extracted/NAR/NAR_BIN2.BIN').read_bytes()
            for lba in (field_report['texture_original_lba'],field_report['texture_mirror_lba']):
                actual=bytearray()
                for i in range((len(expected)+2047)//2048):
                    handle.seek((lba+i)*2352+24);actual+=handle.read(2048)
                assert actual[:len(expected)]==expected,'Original and mirror textures must both remain exact'
    assert sha256(inv['source']['track_path'])==inv['source']['track_sha256']
    result={'candidate':name,'payloads':count,'protected_sectors':len(set(report['changed_lbas'])),
            'original_unchanged':True,'candidate_sha256':sha256(base/(name+'.bin'))}
    if field_report.get('texture_mirror_lba'):result['original_and_mirror_field_textures_exact']=True
    (ROOT/'analysis'/(name.rsplit('-',1)[-1]+'-image-verification.json')).write_text(json.dumps(result,indent=2)+'\n','utf8')
    print(result)


if __name__=='__main__':main()
