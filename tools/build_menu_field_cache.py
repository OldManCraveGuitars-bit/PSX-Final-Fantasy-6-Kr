"""Build the isolated v081 bounded RAM-cache prototype from preserved v080."""
import json,struct,subprocess,shutil
import lz4.block
from textcodec import ROOT
from pac import compress,decompress
from movie_subtitles import msf_word
from small_runtime import compile_runtime
from cdimage import build_image
NAME='FF6-KR-main-development-v081'
SNAP=ROOT/'work/snapshots/v080-before-field-cache'
OUT=ROOT/'work/v081-cache-payloads'
BASE=0x800c8000
def put(b,a,*words):struct.pack_into('<'+'I'*len(words),b,a,*words)
def jump(a,link=False):return ((3 if link else 2)<<26)|((a>>2)&0x3ffffff)
def pad(b):return b+bytes((-len(b))%2048)
def main():
    report=json.loads((ROOT/'work/candidates/FF6-KR-main-development-v080/build-report.json').read_text('utf8'))
    changes={p:(SNAP/'modified'/p).read_bytes() for p in report['changed_files']}
    tool=ROOT/'references/psx-toolchain/bin';prep_elf=ROOT/'work/menu-cache-prepare.elf'
    subprocess.run([str(tool/'mipsel-none-elf-gcc.exe'),'-march=r3000','-mabi=32','-msoft-float','-mno-abicalls','-fno-pic','-G0','-ffreestanding','-fno-builtin','-O2','-Wall','-Wextra','-Werror','-nostdlib',f'-Wl,-T{ROOT.as_posix()}/native/menu-cache-prepare.ld,--build-id=none','-o',str(prep_elf),str(ROOT/'native/menu_cache_prepare.c'),str(ROOT/'native/menu_cache_prepare.S')],check=True)
    script=bytearray(changes['NAR/NAR_BIN3.BIN']);assert len(script)<=0x1fa00
    script+=bytes(0x20000-len(script))
    for section,at,cap in [('bootstrap',0x1fa00,0x80),('prepare',0x1fa80,0x580)]:
        target=ROOT/'work'/('menu-cache-'+section+'.bin')
        subprocess.run([str(tool/'mipsel-none-elf-objcopy.exe'),'-O','binary','-j','.'+section,str(prep_elf),str(target)],check=True)
        b=target.read_bytes();assert len(b)<=cap,(section,len(b),cap);script[at:at+len(b)]=b
    changes['NAR/NAR_BIN3.BIN']=bytes(script)
    prepare_symbols={}
    for line in subprocess.check_output([str(tool/'mipsel-none-elf-nm.exe'),'-n',str(prep_elf)],text=True).splitlines():
        f=line.split()
        if len(f)==3:prepare_symbols[f[2]]=int(f[0],16)&0xffffffff
    menu=bytearray(changes['HAR/MENUMENU.BIN']);har=bytearray(decompress(changes['HAR/HARATA.PAC'])[0])
    old=json.loads((SNAP/'analysis/small-runtime.json').read_text('utf8'))['symbols']
    code,syms=compile_runtime(True)
    assert len(code)<=0x2800,('Main code overlaps translated labels',len(code))
    menu[0x2e000:0x30800]=code+bytes(0x2800-len(code))
    big=(ROOT/'work/menu-big-runtime.bin').read_bytes();assert len(big)<=0x500,len(big)
    menu[0x5f000:0x5f500]=big+bytes(0x500-len(big))
    boost=(ROOT/'work/menu-boost-runtime.bin').read_bytes();menu[0x5f500:0x60000]=boost+bytes(0xb00-len(boost))
    # Retarget every existing native hook whose translated entry moved.
    retarget={jump(v,link):jump(syms[k],link) for k,v in old.items() if k in syms for link in (False,True)}
    for at in range(0,len(har)-3,4):
        w=struct.unpack_from('<I',har,at)[0]
        if w in retarget:put(har,at,retarget[w])
    fullfonts=(ROOT/'work/korean-name-fonts.bin').read_bytes()
    # Build a compact default-name dictionary from the same 30-byte glyphs.
    defaults=struct.unpack_from('<384H',menu,0x25400)
    glyphs={};blocks={}
    for c in sorted(set(defaults)):
        if not 0xac00<=c<=0xd7a3:continue
        block=(c-0xac00)>>8
        if block not in blocks:
            at=struct.unpack_from('<I',fullfonts,24+block*8)[0];blocks[block]=decompress(fullfonts[at:])[0]
        index=(c-0xac00)&255;glyphs[c]=blocks[block][index*30:index*30+30]
    dictionary=struct.pack('<I',len(glyphs))+b''.join(struct.pack('<H',c)+g for c,g in glyphs.items())
    assert len(dictionary)<=0x900
    menu[0x32000:0x34000]=bytes(0x2000)
    jamo=(ROOT/'work/korean-name-jamo.bin').read_bytes();assert len(jamo)==1530
    menu[0x34000:0x52000]=bytes(0x1e000)
    pack=lambda b:lz4.block.compress(bytes(b),mode='high_compression',compression=12,store_size=True)
    parts=[pad(pack(menu[:0x33000])),pad(pack(menu[0x52000:0x60000]))]
    jobs=(ROOT/'work/extracted/HAR/JOBOBJ.BIN').read_bytes()
    # Fixed HAR allocation prevents route/code feedback during compression.
    har_bytes=0x28000;menu_lba=114063+har_bytes//2048
    p1=0;p2=len(parts[0]);job=p2+len(parts[1])
    first=pad(pack(pad(changes['NAR/NAR_BIN.BIN'])))
    second=pad(pack(script))+pad(changes['NAR/NARITA.PAC'])
    font_at=0x40000+len(first)+len(second)
    font=pad(fullfonts);fast_at=font_at+len(font)
    prefix=pad(pack(changes['NAR/NAR_BIN.BIN'][:0x58000]))
    fast=prefix+pad(changes['NAR/NARITA.PAC'])
    routes=dict(MENU_PART1_MSF=msf_word(menu_lba),MENU_PART2_MSF=msf_word(menu_lba+p2//2048),
        MENU_PART1_BYTES=len(parts[0]),MENU_PART2_BYTES=len(parts[1]),
        MENU_PART1_SOURCE=0x80173800-len(parts[0]),MENU_PART2_SOURCE=0x80173800,
        MENU_JOBS_MSF=msf_word(menu_lba+job//2048),MENU_NAME_MSF=msf_word(menu_lba+font_at//2048),MENU_NAME_BYTES=len(font),
        FIELD_CACHE_MSF=msf_word(menu_lba+fast_at//2048),FIELD_CACHE_READ_BYTES=len(fast),
        FIELD_CACHE_PAC_SOURCE=0x800c8000+len(prefix),FIELD_NEAR_TEXTURE_MSF=msf_word(114063+1024))
    assert 0x800c8000+len(fast)<=0x8012c000
    (ROOT/'work/menu-field-cache-routes.h').write_text(''.join(f'#define {k} 0x{v:x}U\n' for k,v in routes.items()),'ascii')
    tool=ROOT/'references/psx-toolchain/bin';elf=ROOT/'work/menu-field-cache.elf'
    subprocess.run([str(tool/'mipsel-none-elf-gcc.exe'),'-march=r3000','-mabi=32','-msoft-float','-mno-abicalls','-fno-pic','-G0','-ffreestanding','-fno-builtin','-O2','-Wall','-Wextra','-Werror','-nostdlib','-I'+str(ROOT/'work'),f'-Wl,-T{ROOT.as_posix()}/native/menu-field-cache.ld,--build-id=none','-o',str(elf),str(ROOT/'native/menu_field_cache.c'),str(ROOT/'native/menu_field_cache.S')],check=True)
    har+=bytes(0x78000-len(har))
    har[0x74000:0x74000+len(dictionary)]=dictionary
    har[0x74900:0x74900+len(jamo)]=jamo
    for section,at,capacity in [('cache_main',0x6d000,0x8000),('cache_return',0x75000,0x1000)]:
        out=ROOT/'work'/f'menu-{section}.bin'
        subprocess.run([str(tool/'mipsel-none-elf-objcopy.exe'),'-O','binary','-j','.'+section,str(elf),str(out)],check=True)
        data=out.read_bytes();assert len(data)<=capacity,(section,len(data));har[at:at+len(data)]=data
    # Use the dedicated job cache at its original late initializer.
    har[0x76000:0x78000]=jobs
    put(har,0x80110c7c-BASE,0x3c04800b,0x34841be8,0x3c058013,0x34a5e000,0x080150eb,0x34062000)
    packed_har=compress(bytes(har));assert len(packed_har)<=har_bytes,len(packed_har)
    changes['HAR/HARATA.PAC']=packed_har+bytes(har_bytes-len(packed_har))
    changes['HAR/MENUMENU.BIN']=bytes(menu)
    exe=bytearray(changes['SLPM_861.98']);base=struct.unpack_from('<I',exe,0x18)[0]
    def patch(a,*w):put(exe,a-base+0x800,*w)
    # HAR is now staged below the two preserved caches. Queue/decode first,
    # then execute the overlay's cache helper before native GPU initialization.
    patch(0x80039ef8,jump(0x80135010,True))
    patch(0x80039be4,jump(0x80135010,True))
    patch(0x80039794,0x3c198014,0x37390000)
    # Size constants in the native CD-table initializer.
    prefix_exe=0x1800
    put(exe,prefix_exe+0x1f34,0x3c080000|(har_bytes>>16),0x35080000|(har_bytes&65535))
    # Prepare the cache while the asynchronous HAR read is in progress.
    # Mode 1 still initializes graphics without touching the live cache.
    patch(0x8003aa74,0x34020002,0x12020008,0,0x3c02801e,0xac402000,
          0x34020001,0x12020007,0,jump(0x8003aab4),0,
          jump(0x801c5c00,True),0,jump(0x8003aaac),0)
    resident=json.loads((SNAP/'analysis/movie-subtitles-runtime.json').read_text('utf8'))['symbols']
    patch(resident['kr_menu_cached'],jump(0x80135008),0)
    patch(resident['kr_menu_read'],jump(0x80135008),0)
    patch(0x80063484,msf_word(menu_lba));patch(0x800634d0,msf_word(114063+1536))
    # Rebuild the original safe full-reload fallback for the new disc routes.
    from field_menu_loading import prepare
    changes['SLPM_861.98']=bytes(exe)
    changes,full_report,banks=prepare(changes,menu_lba,114063+1024)
    assert banks==first+second
    payload=parts[0]+parts[1]+jobs
    assert len(payload)<=0x40000
    payload+=bytes(0x40000-len(payload))+banks+font+fast
    assert har_bytes//2048+(len(payload)+2047)//2048<=1024
    disc=dict(changes);disc['HAR/MENUMENU.BIN']=payload
    relocations={**report['relocations'],'HAR/HARATA.PAC':{'reserve':'DUMMY0.DAT','sector_offset':0},'HAR/MENUMENU.BIN':{'reserve':'DUMMY0.DAT','sector_offset':har_bytes//2048},'NAR/NAR_BIN2.BIN':{'reserve':'DUMMY0.DAT','sector_offset':1024},'OMAKEDIR/OMAKE.PAC':{'reserve':'DUMMY0.DAT','sector_offset':1536}}
    OUT.mkdir(exist_ok=True)
    for p,data in changes.items():
        target=OUT/p;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    (OUT/'menu-disc.bin').write_bytes(payload)
    symbols={}
    for line in subprocess.check_output([str(tool/'mipsel-none-elf-nm.exe'),'-n',str(elf)],text=True).splitlines():
        f=line.split()
        if len(f)==3:symbols[f[2]]=int(f[0],16)&0xffffffff
    metadata=dict(routes=routes,symbols=symbols,prepare_symbols=prepare_symbols,menu_symbols=syms,default_glyphs=len(glyphs),har_read_bytes=har_bytes,menu_part_bytes=list(map(len,parts)),field_fast_read_bytes=len(fast),field_full_read_bytes=len(banks),full_reload=full_report)
    (ROOT/'analysis/v081-field-cache.json').write_text(json.dumps(metadata,indent=2)+'\n','utf8')
    _,built=build_image(ROOT,disc,NAME,relocations=relocations,resizes={'DEODIR/DEO.PAC':0x13000,'BTL/BATTLE.PAC':0x4c000,'NAR/NAR_BIN3.BIN':0x20000})
    folder=ROOT/'work/candidates'/NAME
    report.update(built);report['field_cache']=metadata
    (folder/'build-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8')
    for filename in ('new_dialogue_offsets.json','omake-runtime.bin'):
        shutil.copy2(ROOT/'work/candidates/FF6-KR-main-development-v080'/filename,folder/filename)
    bonus=json.loads((ROOT/'work/candidates/FF6-KR-main-development-v080/omake-insertion.json').read_text('utf8'))
    bonus.update(relocation_lba=114063+1536,relocation_msf=struct.pack('<I',msf_word(114063+1536)).hex())
    (folder/'omake-insertion.json').write_text(json.dumps(bonus,ensure_ascii=False,indent=2)+'\n','utf8')
    print(built['target_sha256'])
if __name__=='__main__':main()
