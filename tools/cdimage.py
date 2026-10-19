"""Raw Mode-2 Form-1 CD protection and guarded in-place extent replacement."""
import struct,hashlib,shutil,json
from pathlib import Path
SYNC=bytes.fromhex('00ffffffffffffffffffff00')
F=[(i<<1)^(0x11d if i&128 else 0) for i in range(256)]
B={i^F[i]:i for i in range(256)}
EDC=[]
for i in range(256):
    x=i
    for _ in range(8):x=(x>>1)^(0xd8018001 if x&1 else 0)
    EDC.append(x)
def parity(data,majors,minors,step,inc):
    out=bytearray(majors*2)
    for major in range(majors):
        p=(major//2)*step+major%2;a=b=0
        for _ in range(minors):
            v=data[p];p=(p+inc)%(majors*minors);a=F[a^v];b^=v
        a=B[F[a]^b];out[major]=a;out[major+majors]=a^b
    return out
def protect(raw):
    if len(raw)!=2352 or raw[:12]!=SYNC or raw[15]!=2 or raw[18]&0x20:raise ValueError('Not Form 1')
    out=bytearray(raw);edc=0
    for b in out[16:2072]:edc=(edc>>8)^EDC[(edc^b)&255]
    struct.pack_into('<I',out,2072,edc)
    data=bytes(4)+out[16:2076];out[2076:2248]=parity(data,86,24,2,86)
    out[2248:2352]=parity(data+out[2076:2248],52,43,86,88)
    return out
def sha256(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(2**20),b''):h.update(b)
    return h.hexdigest()
def directory_records(handle):
    """Return ISO directory-record byte positions without changing the source."""
    def block(lba):
        handle.seek(lba*2352+24);return handle.read(2048)
    pvd=block(16)
    if pvd[:7]!=b'\x01CD001\x01':raise ValueError('ISO PVD guard')
    root_lba,root_size=struct.unpack_from('<I',pvd,158)[0],struct.unpack_from('<I',pvd,166)[0]
    records={};queue=[('',root_lba,root_size)];visited=set()
    while queue:
        parent,lba,size=queue.pop(0)
        if lba in visited:continue
        visited.add(lba)
        for sector in range((size+2047)//2048):
            data=block(lba+sector);at=0
            while at<2048 and data[at]:
                length=data[at]
                if length<34 or at+length>2048:raise ValueError('ISO record boundary')
                record=data[at:at+length];identifier=record[33:33+record[32]]
                if identifier not in (b'\0',b'\1'):
                    filename=identifier.decode('ascii').split(';',1)[0]
                    path=parent+'/'+filename if parent else filename
                    extent=struct.unpack_from('<I',record,2)[0];count=struct.unpack_from('<I',record,10)[0]
                    records[path]=(lba+sector,at,extent,count)
                    if record[25]&2:queue.append((path,extent,count))
                at+=length
    return records

def build_image(root,changes,name,relocations=None,resizes=None):
    inv=json.loads((root/'analysis/disc_inventory.json').read_text('utf-8'));src=Path(inv['source']['track_path'])
    if sha256(src)!=inv['source']['track_sha256']:raise ValueError('Original hash mismatch')
    outdir=root/'work/candidates'/name;outdir.mkdir(parents=True,exist_ok=True);target=outdir/(name+'.bin')
    shutil.copyfile(src,target);edits=[];relocations=relocations or {};resizes=resizes or {};resized={}
    with target.open('r+b') as f:
        records=directory_records(f)
        used_reserves={}
        def write_sector(lba,payload):
            f.seek(lba*2352);raw=f.read(2352)
            if protect(raw)!=raw:raise ValueError(f'Sector protection invalid at {lba}')
            data=bytearray(raw);data[24:2072]=payload
            f.seek(lba*2352);f.write(protect(data));edits.append(lba)
        def update_record(path,lba,size):
            sector,at,_,_=records[path]
            f.seek(sector*2352+24);payload=bytearray(f.read(2048))
            struct.pack_into('<I',payload,at+2,lba);struct.pack_into('>I',payload,at+6,lba)
            struct.pack_into('<I',payload,at+10,size);struct.pack_into('>I',payload,at+14,size)
            write_sector(sector,payload)
        # Several overlays may occupy distinct ranges of the same dummy file.
        # Validate all ranges before writing any replacement sectors.
        for path,destination in relocations.items():
            reserve=destination if isinstance(destination,str) else destination['reserve']
            offset=0 if isinstance(destination,str) else destination.get('sector_offset',0)
            if reserve not in ('DUMMY0.DAT','DUMMY1.DAT','DUMMY2.DAT') or offset<0:raise ValueError('Not a designated dummy allocation')
            space=next(x for x in inv['entries'] if x['path']==reserve)
            sectors=(len(changes[path])+2047)//2048
            if (offset+sectors)*2048>=space['size']:raise ValueError('Dummy reserve overflow')
            ranges=used_reserves.setdefault(reserve,[])
            if any(offset<hi and lo<offset+sectors for lo,hi in ranges):raise ValueError('Overlapping dummy allocations')
            ranges.append((offset,offset+sectors))
        for path,new in changes.items():
            entry=next(x for x in inv['entries'] if x['path']==path)
            if path in relocations:
                destination=relocations[path]
                reserve=destination if isinstance(destination,str) else destination['reserve']
                offset=0 if isinstance(destination,str) else destination.get('sector_offset',0)
                space=next(x for x in inv['entries'] if x['path']==reserve)
                sectors=(len(new)+2047)//2048
                for i in range(sectors):
                    chunk=new[i*2048:(i+1)*2048]
                    write_sector(space['extent_lba']+offset+i,chunk+bytes(2048-len(chunk)))
                update_record(path,space['extent_lba']+offset,len(new))
                continue
            if len(new)!=entry['size']:
                allocated=((entry['size']+2047)//2048)*2048
                if path not in resizes or not entry['size']<=len(new)<=resizes[path]<=allocated:
                    raise ValueError(f'Extent size changed without a safe allocation: {path}')
                resized[path]={'old_size':entry['size'],'new_size':len(new),'allocated_size':allocated}
            old=(root/'work/extracted'/path).read_bytes()
            for i in range((len(new)+2047)//2048):
                start=i*2048;end=min(start+2048,len(new))
                if old[start:end]==new[start:end]:continue
                lba=entry['extent_lba']+i;f.seek(lba*2352);raw=f.read(2352)
                if protect(raw)!=raw:raise ValueError(f'Original sector protection invalid at {lba}')
                data=bytearray(raw);data[24:24+end-start]=new[start:end];newraw=protect(data)
                f.seek(lba*2352);f.write(newraw);edits.append(lba)
            if path in resized:update_record(path,entry['extent_lba'],len(new))
        for reserve,ranges in used_reserves.items():
            space=next(x for x in inv['entries'] if x['path']==reserve);end=max(hi for lo,hi in ranges)
            update_record(reserve,space['extent_lba']+end,space['size']-end*2048)
    (outdir/(name+'.cue')).write_text(f'FILE "{name}.bin" BINARY\n  TRACK 01 MODE2/2352\n    INDEX 01 00:00:00\n','ascii')
    edits=sorted(set(edits))
    report={'status':'development_candidate','original_sha256':inv['source']['track_sha256'],'target_sha256':sha256(target),'changed_files':list(changes),'relocations':relocations,'resized_files':resized,'changed_sector_count':len(edits),'changed_lbas':edits}
    (outdir/'build-report.json').write_text(json.dumps(report,indent=2)+'\n','utf-8')
    return target,report
