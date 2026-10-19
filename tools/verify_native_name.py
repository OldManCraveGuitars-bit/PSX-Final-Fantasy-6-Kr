"""Compile for the PSX R3000 and execute the name composer as MIPS code."""
import json, random, struct, subprocess
from pathlib import Path
from unicorn import Uc, UC_ARCH_MIPS, UC_MODE_MIPS32, UC_MODE_LITTLE_ENDIAN
from unicorn.mips_const import UC_MIPS_REG_A0, UC_MIPS_REG_A1, UC_MIPS_REG_RA, UC_MIPS_REG_SP, UC_MIPS_REG_V0
from hangul_name import HangulName, LEADS, VOWELS, FINALS
from textcodec import ROOT

TOOLCHAIN=ROOT/'references/psx-toolchain/bin'
STATE=0x801e0000
OUTPUT=STATE+0x100
RETURN=0x801fffc0

def build():
    elf=ROOT/'work/hangul-name.elf'
    subprocess.run([str(TOOLCHAIN/'mipsel-none-elf-gcc.exe'),'-march=r3000','-mabi=32',
        '-msoft-float','-mno-abicalls','-fno-pic','-G0','-ffreestanding','-fno-builtin',
        '-O2','-Wall','-Wextra','-Werror','-nostdlib',
        '-Wl,-Ttext=0x80180000,-e,hn_init,--build-id=none','-o',str(elf),
        str(ROOT/'native/hangul_name.c')],check=True)
    symbols={}
    listing=subprocess.check_output([str(TOOLCHAIN/'mipsel-none-elf-nm.exe'),'-n',str(elf)],text=True)
    for line in listing.splitlines():
        fields=line.split()
        if len(fields)==3:symbols[fields[2]]=int(fields[0],16)&0xffffffff
    (ROOT/'analysis/native-name-symbols.json').write_text(json.dumps(symbols,indent=2)+'\n','utf8')
    binary=elf.read_bytes()
    uc=Uc(UC_ARCH_MIPS,UC_MODE_MIPS32|UC_MODE_LITTLE_ENDIAN)
    uc.mem_map(0,0x200000)
    phoff=struct.unpack_from('<I',binary,28)[0]
    phsize,phcount=struct.unpack_from('<HH',binary,42)
    loaded=0
    for i in range(phcount):
        kind,off,addr,_,size,_,_,_=struct.unpack_from('<8I',binary,phoff+i*phsize)
        if kind==1 and size and (addr&0x1fffffff)+size<=0x200000:
            uc.mem_write(addr&0x1fffffff,binary[off:off+size]);loaded+=size
    return uc,symbols,loaded

def main():
    uc,symbols,size=build()
    def call(name,a1=0):
        uc.reg_write(UC_MIPS_REG_SP,0x801ff000)
        uc.reg_write(UC_MIPS_REG_RA,RETURN)
        uc.reg_write(UC_MIPS_REG_A0,STATE)
        uc.reg_write(UC_MIPS_REG_A1,a1)
        uc.emu_start(symbols[name],RETURN,count=5000)
        return uc.reg_read(UC_MIPS_REG_V0)&0xffffffff
    def text():
        n=call('hn_text',OUTPUT)
        return bytes(uc.mem_read(OUTPUT&0x1fffffff,n*2)).decode('utf-16le')
    def init(limit=6):call('hn_init',limit)
    def feed(key):return call('hn_feed',ord(key))
    cases=0
    # Every modern Hangul syllable, including complex finals, must be reachable.
    for l in LEADS:
        for v in VOWELS:
            for t in FINALS:
                init(); reference=HangulName()
                # A compound final is entered using the two selected consonants.
                from hangul_name import T_SPLIT
                keys=l+v+(''.join(T_SPLIT[t]) if t in T_SPLIT else t)
                for key in keys:
                    assert feed(key)==reference.feed(key)
                assert text()==reference.text,(keys,text(),reference.text)
                cases+=1
    rng=random.Random(86198)
    operations=0
    for _ in range(300):
        limit=rng.randrange(1,7);init(limit);reference=HangulName(limit)
        for _ in range(50):
            if rng.randrange(4)==0:
                call('hn_backspace');reference.backspace()
            else:
                key=rng.choice(LEADS+VOWELS+[' ','A','1','\u3000'])
                assert feed(key)==reference.feed(key)
            assert text()==reference.text,(text(),reference.text)
            operations+=1
        n=call('hn_confirm',OUTPUT)
        actual=bytes(uc.mem_read(OUTPUT&0x1fffffff,n*2)).decode('utf-16le')
        try:expected=reference.confirm()
        except ValueError:expected=''
        assert actual==expected,(actual,expected)
    report={'target':'PSX R3000 MIPS I','loaded_bytes':size,'syllables_passed':cases,
        'mixed_input_backspace_operations':operations,'native_ui_integrated':False,
        'save_load_integrated':False}
    (ROOT/'analysis/native-name-verification.json').write_text(json.dumps(report,indent=2)+'\n','utf8')
    print(report)

if __name__=='__main__':main()
