"""Resident subtitle bootstrap plus a separately loaded 12x12 font/cue bank."""
import json,struct,subprocess
from textcodec import ROOT
from korean_codec import raster,normalize
from caption_format import MOVIES,pack_caption_text,validate_caption_rows

RESERVE_LBA=130079
PREFIX=0x1800
LOAD_ADDRESS=0x80038000-PREFIX
FONT_FILE_OFFSET=0x37000

def msf_word(lba):
    minute,remainder=divmod(lba+150,4500);second,frame=divmod(remainder,75)
    def bcd(n):return (n//10)*16+n%10
    return bcd(minute)|(bcd(second)<<8)|(bcd(frame)<<16)

def caption_data(cues):
    data,mapping,font_offset=pack_caption_text(cues)
    for c,code in mapping.items():
        if c in (' ','\n'):continue
        glyph=raster(c)
        for y in range(12):
            row=sum(2048>>x for x in range(12) if y<11 and glyph.getpixel((x,y)))
            struct.pack_into('<H',data,font_offset+(code-2)*24+y*2,row)
    return data

def prepare():
    first=RESERVE_LBA+FONT_FILE_OFFSET//2048
    (ROOT/'work/movie-bank-routes.h').write_text(
        ''.join(f'#define MOVIE_{movie}_MSF 0x{msf_word(first+i*2):08x}U\n' for i,movie in enumerate(MOVIES)),'ascii')
    tool=ROOT/'references/psx-toolchain/bin';elf=ROOT/'work/movie-subtitles.elf'
    decoder=ROOT/'work/menu-lz4.elf'
    subprocess.run([str(tool/'mipsel-none-elf-gcc.exe'),'-march=r3000','-mabi=32','-mno-abicalls','-fno-pic','-G0','-nostdlib',
        f'-Wl,-T{ROOT.as_posix()}/native/menu-lz4.ld,--build-id=none','-o',str(decoder),str(ROOT/'native/menu_lz4.S')],check=True)
    subprocess.run([str(tool/'mipsel-none-elf-objcopy.exe'),'-O','binary',str(decoder),str(ROOT/'work/menu-lz4.bin')],check=True)
    if (ROOT/'work/menu-lz4.bin').stat().st_size>0x180:raise ValueError('Menu decoder allocation overflow')
    subprocess.run([str(tool/'mipsel-none-elf-gcc.exe'),'-march=r3000','-mabi=32','-msoft-float','-mno-abicalls','-fno-pic','-G0',
        '-ffreestanding','-fno-builtin','-Os','-Wall','-Wextra','-Werror','-nostdlib','-I'+str(ROOT/'work'),
        f'-Wl,-T{ROOT.as_posix()}/native/movie-subtitles.ld,--build-id=none','-o',str(elf),
        str(ROOT/'native/movie_subtitles.c'),str(ROOT/'native/movie_subtitles.S'),str(ROOT/'native/boost_gameplay.S')],check=True)
    target=ROOT/'work/movie-subtitles.bin'
    subprocess.run([str(tool/'mipsel-none-elf-objcopy.exe'),'-O','binary',str(elf),str(target)],check=True)
    code=target.read_bytes()
    if len(code)>0x800:raise ValueError(('Resident subtitle bootstrap overflow',len(code),0x800))
    symbols={}
    for line in subprocess.check_output([str(tool/'mipsel-none-elf-nm.exe'),'-n',str(elf)],text=True).splitlines():
        f=line.split()
        if len(f)==3:symbols[f[2]]=int(f[0],16)&0xffffffff
    source=ROOT/'translations/movie-subtitles.ko.json'
    cues=json.loads(source.read_text('utf8')) if source.exists() else []
    validate_caption_rows(cues)
    data=b''.join(caption_data([r for r in cues if r.get('movie','OPERA')==movie]) for movie in MOVIES)
    (ROOT/'work/movie-caption-data.bin').write_bytes(data)
    report={'renderer':'independent native GPU LoadImage captions after MDEC transfer; original STR untouched',
        'font':'Galmuri9','glyph_cell':[12,12],'space_pixels':6,'cue_count':len(cues),'cue_review':'pending' if not cues else 'frame alignment pending',
        'runtime_address':'0x80037800','runtime_bytes':len(code),'bank_address':'0x80033000','bank_bytes':4096,
        'bank_count':len(MOVIES),'maximum_rows':2,'line_pitch':14,'format_version':2,
        'movies':{movie:{'cue_count':sum(r.get('movie','OPERA')==movie for r in cues),'bank_lba':RESERVE_LBA+FONT_FILE_OFFSET//2048+i*2} for i,movie in enumerate(MOVIES)},
        'preserved_scratch_bytes':18432,'subtitle_data_lba':RESERVE_LBA+FONT_FILE_OFFSET//2048,
        'symbols':symbols,'native_verification':'pending'}
    (ROOT/'analysis/movie-subtitles-runtime.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8')
    return code,data,report

def patch(changes):
    code,data,report=prepare()
    exe=bytearray(changes['SLPM_861.98'])
    at=0x8003a1fc-0x80038000+0x800
    if exe[at:at+8]!=bytes.fromhex('cbeb000c21300000'):raise ValueError('Menu read hook guard')
    struct.pack_into('<I',exe,at,(3<<26)|((report['symbols']['kr_menu_cached']>>2)&0x3ffffff))
    at=0x8003a9ac-0x80038000+0x800
    if exe[at:at+8]!=bytes.fromhex('1a80033c1eea6334'):raise ValueError('Battle data shift guard')
    struct.pack_into('<II',exe,at,(2<<26)|((report['symbols']['kr_battle_data_shift']>>2)&0x3ffffff),0)
    at=0x800455f4-0x80038000+0x800
    if exe[at:at+8]!=bytes.fromhex('c8ffbd271800b0af'):raise ValueError('Movie entry guard')
    struct.pack_into('<II',exe,at,(2<<26)|((report['symbols']['kr_movie_play']>>2)&0x3ffffff),0)
    at=0x80045dec-0x80038000+0x800
    if exe[at:at+8]!=bytes.fromhex('0800828c00000000'):raise ValueError('Movie STR frame hook guard')
    struct.pack_into('<II',exe,at,(2<<26)|((report['symbols']['kr_movie_frame']>>2)&0x3ffffff),0)
    header=bytearray(exe[:0x800]);struct.pack_into('<II',header,0x18,LOAD_ADDRESS,0x34000+PREFIX)
    prefix=bytearray(PREFIX)
    preview=(ROOT/'work/psx-name-runtime.bin').read_bytes();at=0x80036c20-LOAD_ADDRESS
    if at+len(preview)>0x80037680-LOAD_ADDRESS:raise ValueError('PSX preview/menu decoder code overlap')
    prefix[at:at+len(preview)]=preview
    decoder=(ROOT/'work/menu-lz4.bin').read_bytes();at=0x80037680-LOAD_ADDRESS;prefix[at:at+len(decoder)]=decoder
    at=0x80037800-LOAD_ADDRESS;prefix[at:at+len(code)]=code
    expanded=header+prefix+exe[0x800:]
    if len(expanded)>FONT_FILE_OFFSET:raise ValueError('EXE subtitle bank offset')
    expanded+=bytes(FONT_FILE_OFFSET-len(expanded))+data
    result=dict(changes);result['SLPM_861.98']=bytes(expanded)
    report['executable_relocation']='DUMMY2.DAT'
    (ROOT/'analysis/movie-subtitles-runtime.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8')
    return result

if __name__=='__main__':
    _,_,report=prepare();print({k:v for k,v in report.items() if k!='symbols'})
