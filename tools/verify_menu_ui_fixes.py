"""Execute native title copies and mixed canvas/font GPU lists on the R3000."""
import json,struct,sys,os
from unicorn import Uc,UC_ARCH_MIPS,UC_MODE_MIPS32,UC_MODE_LITTLE_ENDIAN
from unicorn.mips_const import *
from emu import ROOT
from pac import decompress
from small_text import ascii_glyphs

def main():
    folder=ROOT/os.environ.get('FF6_QA_PAYLOADS', 'work/'+('ui-fix' if '--preview' in sys.argv else 'modified'))
    u=Uc(UC_ARCH_MIPS,UC_MODE_MIPS32|UC_MODE_LITTLE_ENDIAN);u.mem_map(0,0x200000)
    ram=(ROOT/'work/item-header-before-fix-memory/ram.bin').read_bytes()
    u.mem_write(0,ram)
    menu=(folder/'HAR/MENUMENU.BIN').read_bytes()
    overlay=decompress((folder/'HAR/HARATA.PAC').read_bytes())[0]
    u.mem_write(0xc8000,overlay);u.mem_write(0x140000,menu)
    # Title-copy bookkeeping queues a task after writing the native buffer.
    u.mem_write(0x1148fc,bytes.fromhex('0800e00300000000'))
    report=json.loads((ROOT/'analysis/small-runtime.json').read_text('utf8'))
    mapping=report['mapping'];aliases=json.loads((ROOT/'analysis/small-text-insertion.json').read_text('utf8'))['aliases']
    aliases={int(v,16):mapping[c] for c,v in aliases.items()}
    ascii_table=ascii_glyphs()
    def invoke(address,args=(),x=512,y=0):
        u.reg_write(UC_MIPS_REG_SP,0x801ff000);u.reg_write(UC_MIPS_REG_RA,0x801fffc0)
        u.reg_write(UC_MIPS_REG_S6,x);u.mem_write(0x1ff028,struct.pack('<H',y))
        for reg,value in zip([UC_MIPS_REG_A0,UC_MIPS_REG_A1,UC_MIPS_REG_A2,UC_MIPS_REG_A3],args):u.reg_write(reg,value)
        u.emu_start(address,0x801fffc0,count=100000)
        assert u.reg_read(UC_MIPS_REG_PC)==0x801fffc0,hex(u.reg_read(UC_MIPS_REG_PC))
    jobs=json.loads((ROOT/'translations/menu-jobs.ko.json').read_text('utf8'))
    for i in range(64):
        u.mem_write(0x6c1a0,struct.pack('<I',0x801ee000));u.mem_write(0x1ee000,struct.pack('<H',0xf600))
        u.mem_write(0x2f600,bytes((i,)));u.mem_write(0x30181,struct.pack('<H',0x7ecb))
        u.mem_write(0x27ec9,struct.pack('<H',0x1040)+bytes(30))
        invoke(0x800d7dd8)
        stub=bytes(u.mem_read(0x27ecb,7))
        assert stub==menu[0x19b1b+i*7:0x19b22+i*7],(i,stub.hex())
        u.mem_write(0x2e0e7,bytes.fromhex('c97e02'));u.mem_write(0x2e000,b'\0\0');u.mem_write(0x2e029,b'\x20')
        invoke(0x800f5ae0)
        text=jobs[str(i)]['translation']
        actual=struct.unpack('<'+'H'*(len(text)+1),u.mem_read(0x21040,2*(len(text)+1)))
        expected=tuple((0x8ffe if c==' ' else 0xa000|(mapping[c] if ord(c)>127 else ascii_table[ord(c)])) for c in text)+(0xcfff,)
        assert actual==expected,(i,text,actual,expected)
    cases=0
    for frame in [0,1]:
        base=[0x8006f698,0x8008bd54][frame]
        u.mem_write(0x6c0d4,struct.pack('<I',frame))
        for pagex,pagey in [(512,0),(768,256)]:
            for y in [0,1,7,8,12]:
                for height in [1,7,8,13]:
                    u.mem_write(0x30107,b'\x40')
                    # A native canvas tile and a Korean tile deliberately share
                    # index 100. Only the latter must change texture pages.
                    row=struct.pack('<6H',0x2100,0xa100,0x8ffe,0xa101,0xcfff,0)+bytes(52)
                    u.mem_write(0xb3be8,row*32)
                    u.mem_write(0x12e398,b'\0\0');u.mem_write(0x1a0000,bytes(0x8000))
                    u.mem_write((base&0x1fffff)+0x70,struct.pack('<I',0x00ffffff))
                    u.mem_write(0x1e0100,struct.pack('<4h',0,y,40,height))
                    u.mem_write(0x1ff010,struct.pack('<3I',20,0,0))
                    invoke(0x80120144,[base,0x801e0100,0,40],pagex,pagey)
                    count=struct.unpack('<H',u.mem_read(0x12e398,2))[0]
                    assert count and count%3==0,(y,height,count)
                    for n in range(count):
                        address=(base&0x1fffff)+0x20d0+n*20
                        packet=bytes(u.mem_read(address,20));head=struct.unpack_from('<I',packet)[0]
                        x=struct.unpack_from('<h',packet,8)[0]
                        assert x==[40,48,60][n%3],(n,x)
                        pool=0x1a0000+frame*0x4000+n*16
                        primary,cmd,restore,cmd2=struct.unpack('<4I',u.mem_read(pool,16))
                        if pagex==768 and n%3:
                            assert cmd==0xe1000008 and cmd2==0xe100001c,(hex(cmd),hex(cmd2))
                            assert primary==0x01000000|address
                            assert head&0xffffff==pool+8
                            assert restore>>24==1
                        else:
                            assert not any(u.mem_read(pool,16)),(pagex,n)
                    cases+=1
    result={'native_job_title_copy_and_expansion':64,'mixed_canvas_font_render_cases':cases,
        'original_canvas_texture_pages':'preserved','Korean_font_texture_page':'512,0',
        'double_buffered_GPU_nodes':'passed','small_space_pixels':4}
    (ROOT/'analysis/menu-ui-fixes-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n','utf8')
    print(result)

if __name__=='__main__':main()
