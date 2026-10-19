"""Run the real menu copy/draw routines and inspect their GPU sprite packets."""
import json,struct
from unicorn import Uc,UC_ARCH_MIPS,UC_MODE_MIPS32,UC_MODE_LITTLE_ENDIAN
from unicorn.mips_const import UC_MIPS_REG_A0,UC_MIPS_REG_A1,UC_MIPS_REG_A2,UC_MIPS_REG_A3,UC_MIPS_REG_SP,UC_MIPS_REG_RA,UC_MIPS_REG_PC
from textcodec import ROOT
from pac import decompress
import os
PAYLOADS = ROOT / os.environ.get("FF6_QA_PAYLOADS", "work/modified")
from small_ui import LABELS

def main():
    ram=(ROOT/'work/v009-galmuri7-menu-memory/ram.bin').read_bytes()
    overlay=decompress((PAYLOADS/'HAR/HARATA.PAC').read_bytes())[0]
    menu=(PAYLOADS/'HAR/MENUMENU.BIN').read_bytes()
    report=json.loads((ROOT/'analysis/small-runtime.json').read_text('utf8'));mapping=report['mapping']
    u=Uc(UC_ARCH_MIPS,UC_MODE_MIPS32|UC_MODE_LITTLE_ENDIAN);u.mem_map(0,0x200000);u.mem_write(0,ram)
    u.mem_write(0xc8000,overlay);u.mem_write(0x140000,menu)
    def invoke(address,args):
        u.reg_write(UC_MIPS_REG_SP,0x801ff000);u.reg_write(UC_MIPS_REG_RA,0x801fffc0)
        for reg,value in zip([UC_MIPS_REG_A0,UC_MIPS_REG_A1,UC_MIPS_REG_A2,UC_MIPS_REG_A3],args):u.reg_write(reg,value)
        u.emu_start(address,0x801fffc0,count=100000)
        assert u.reg_read(UC_MIPS_REG_PC)==0x801fffc0,'Routine did not return'
    # Exercise the actual tagged-record hook and the six native in-place labels.
    for offset,_,text in LABELS:
        source=0x800c8000+offset
        source=int(report['label_pointers'].get(hex(source),hex(source)),16)
        xy=struct.unpack('<H',u.mem_read(source&0x1fffffff,2))[0]
        u.mem_write(0x2e0e7,struct.pack('<I',source&0xffffff)[:3]);u.mem_write(0x2e000,b'\0\0');u.mem_write(0x2e029,b'\x20')
        for entry in [0x800f5ae0,0x800f5fc8]:
            u.mem_write(0x2e0e7,struct.pack('<I',source&0xffffff)[:3])
            invoke(entry,[])
            destination=0x20000+xy+(0x40 if entry==0x800f5fc8 else 0)
            result=struct.unpack('<'+'H'*(len(text)+1),u.mem_read(destination,2*(len(text)+1)))
            assert result==tuple([0xa000|mapping[c] for c in text]+[0xcfff]),(text,hex(entry),result)
    # A space consumes four pixels, and the next independent label keeps its X.
    # Both partial-row and whole-row drawing paths must produce the same origins.
    u.mem_write(0x30107,b'\x40')
    row=struct.pack('<6H',0xa100,0x8ffe,0xa101,0xcfff,0xa102,0)+bytes(52)
    u.mem_write(0xb3be8,row*32)
    cases=0
    for y in [0,1,7,8,12]:
        for height in [1,7,8,13]:
            # This write-only packet pool is deliberately no longer read from
            # CD. Stale field bytes must not affect any generated sprite.
            u.mem_write(0x1a0000,b'\xa5'*0x8000)
            u.mem_write(0x12e398,b'\0\0')
            u.mem_write(0x1e0100,struct.pack('<4h',0,y,40,height))
            u.mem_write(0x1ff010,struct.pack('<3I',20,0,0))
            invoke(0x80120144,[0x801a0000,0x801e0100,0,40])
            count=struct.unpack('<H',u.mem_read(0x12e398,2))[0]
            xs=[struct.unpack('<h',u.mem_read(0x1a20d8+i*20,2))[0] for i in range(count)]
            assert count>0 and count%3==0,(y,height,count)
            assert xs==[40,52,72]*(count//3),(y,height,xs)
            cases+=1
    result={'target':'native PSX MIPS menu routines','tagged_labels_passed':len(LABELS),
        'clipped_render_cases_passed':cases,'space_pixels':4,'glyph_origins_for_새_게임':[0,12,20],
        'independent_label_position_preserved':True}
    result['uninitialized_packet_pool_cases']=cases
    (ROOT/'analysis/native-small-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n','utf8')
    print(result)

if __name__=='__main__':main()
