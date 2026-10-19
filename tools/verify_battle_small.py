"""Execute battle name hooks, Hangul cache handling and native sprite spacing."""
import json,struct
from unicorn import Uc,UC_ARCH_MIPS,UC_MODE_MIPS32,UC_MODE_LITTLE_ENDIAN
from unicorn.mips_const import *
from textcodec import ROOT
from pac import decompress

def main():
    ram=(ROOT/'work/battle-native-original-memory/ram.bin').read_bytes()
    overlay=decompress((ROOT/'work/modified/BTL/BATTLE.PAC').read_bytes())[0]
    data=(ROOT/'work/modified/BTL/FF6_BTL.BIN').read_bytes()
    report=json.loads((ROOT/'analysis/battle-small-runtime.json').read_text('utf8'))
    symbols=report['symbols'];u=Uc(UC_ARCH_MIPS,UC_MODE_MIPS32|UC_MODE_LITTLE_ENDIAN)
    u.mem_map(0,0x200000);u.mem_map(0x1f800000,0x1000);u.mem_write(0,ram)
    u.mem_write(0xc8000,overlay);u.mem_write(0x197c00,data)
    # VSync(-1) is an external hardware clock, irrelevant to packet spacing.
    u.mem_write(0x59820,struct.pack('<II',0x03e00008,0x00001021))
    u.mem_write(0x6c1a0,struct.pack('<I',0x1f8003cc))
    def invoke(address,args=()):
        u.reg_write(UC_MIPS_REG_SP,0x801ff000);u.reg_write(UC_MIPS_REG_RA,0x801fffc0)
        for reg,value in zip([UC_MIPS_REG_A0,UC_MIPS_REG_A1,UC_MIPS_REG_A2,UC_MIPS_REG_A3],args):u.reg_write(reg,value)
        u.emu_start(address,0x801fffc0,count=100000)
        assert u.reg_read(UC_MIPS_REG_PC)==0x801fffc0
        assert u.reg_read(UC_MIPS_REG_SP)==0x801ff000
    def expected(row,width,palette=0x2000):
        stream=bytes.fromhex(row['hex']);p=1;tiles=[]
        while stream[p] and len(tiles)<width:
            c=stream[p];p+=1
            if c==32:tile=0x8ffe
            elif 2<=c<=0x1a:tile=256+u.mem_read(0x19b780+c-2,1)[0]
            elif 0x1c<=c<=0x1f:tile=((c-0x1c)<<8)|stream[p];p+=1
            elif c==0x1b:tile=256+stream[p];p+=1
            elif c>=0x80:tile=struct.unpack('<H',u.mem_read(0x19b600+(c-0x80)*2,2))[0]
            else:tile=256+u.mem_read(0x19b700+c,1)[0]
            if tile!=0x8ffe and (tile>=512 or 352<=tile<448):tile|=0x8000
            tiles.append(tile if tile==0x8ffe else tile|palette)
        return tiles+[0x21ff]*(width-len(tiles))
    cases=0
    routes={'monster': [('kr_battle_monster',8,0),('kr_battle_monster_list',8,1)],
        'command':[('kr_battle_command',6,0)],'spell':[('kr_battle_spell_list',9,1),('kr_battle_spell_short',5,1),('kr_battle_spell_menu',5,0)],
        'item':[('kr_battle_item_list',9,1),('kr_battle_item_menu',9,0)]}
    sizes={'monster':8,'command':6,'spell':5,'item':9}
    for row in report['records']:
        for function,width,list_mode in routes.get(row['category'],[]):
            u.mem_write(0x1f8003cc,b'\0\0');u.mem_write(0x2e04a,struct.pack('<HHB',0x4000,0x4040,0x21))
            u.mem_write(0x2e051,struct.pack('<HHH',0x4000,0x4040,0x21ff))
            invoke(symbols[function],[row['index']*sizes[row['category']]])
            result=list(struct.unpack('<'+'H'*width,u.mem_read(0x24040,width*2)))
            assert result==expected(row,width),(row['id'],function,result,expected(row,width))
            assert struct.unpack('<H',u.mem_read(0x1f8003cc,2))[0]==width*2
            cases+=1
    # Use the original native renderer rather than a simulated glyph loop.
    u.mem_write(0x19b7a0,struct.pack('<I',0x3142544b));u.mem_write(0x30107,b'\x40')
    row=struct.pack('<6H',0x2200,0x8ffe,0x2201,0x21ff,0x2202,0x21ff)+b'\xff\x21'*26
    u.mem_write(0xbabe8,row*32)
    for y,height in [(0,8),(1,7),(7,8),(8,16)]:
        u.mem_write(0x196be4,b'\0\0');u.mem_write(0x1d0000,struct.pack('<4h',0,y,40,height))
        u.mem_write(0x1ff010,bytes(16));invoke(0x80156820,[0x8006f698,0x801d0000,40,151])
        count=struct.unpack('<H',u.mem_read(0x196be4,2))[0]
        xs=[struct.unpack('<h',u.mem_read(0x6f698+0x20d0+i*20+8,2))[0] for i in range(count)]
        assert count>0 and xs==[40,52,72]*(count//3),(y,height,count,xs)
    # The native global sprite counter begins at 1000. Korean routing uses
    # its own reset counter, never the unrelated total primitive count.
    page_cases=0
    for db in (0,1):
        for y,height in [(0,8),(1,7),(7,8),(8,16)]:
            base=(0x8006f698,0x8008bd54)[db]
            u.mem_write(0x6c0d4,struct.pack('<I',db))
            u.mem_write(0x196be4,struct.pack('<H',1200))
            u.mem_write(0x19b7ac,bytes(4));u.mem_write(0x1e0800,bytes(0x4000))
            u.mem_write(0x18ef3c,struct.pack('<I',0x00ffffff)*20)
            u.mem_write(0xbabe8,struct.pack('<5H',0x2200,0xa200,0x8ffe,0xa201,0x21ff)+b'\xff\x21'*27)
            u.mem_write(0xbac28,bytes(u.mem_read(0xbabe8,64)))
            u.mem_write(0x1d0000,struct.pack('<4h',0,y,40,height))
            invoke(0x80156820,[base,0x801d0000,40,151])
            count=struct.unpack('<I',u.mem_read(0x19b7ac,4))[0]
            assert count and count<=4,(y,height,count)
            for i in range(count):
                pool=0x1e0800+db*0x2000+i*16
                head,page,restore,original=struct.unpack('<4I',u.mem_read(pool,16))
                sprite=head&0xffffff
                assert page==0xe100000b and original==0xe100001a
                assert head>>24==1 and restore>>24==1
                assert struct.unpack('<I',u.mem_read(sprite,4))[0]==0x04000000|pool+8
                assert struct.unpack('<h',u.mem_read(sprite+8,2))[0] in (48,60)
            # A native canvas sprite with identical low tile bits is untouched.
            first=(base&0x1fffff)+0x20d0+1200*20
            assert not 0x1e0800<=struct.unpack('<I',u.mem_read(first,4))[0]&0xffffff<0x1e4800
            page_cases+=1
    result={'native_name_output_cases':cases,'native_sprite_spacing_cases':4,'space_pixels':4,
        'canvas_and_Korean_page_isolation_cases':page_cases,'native_sprite_counter_over_1200':True,
        'physical_gameplay_verification':'command and monster output observed; broader paths pending'}
    (ROOT/'analysis/battle-small-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n','utf8')
    print(result)
if __name__=='__main__':main()
