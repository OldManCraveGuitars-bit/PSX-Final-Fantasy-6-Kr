"""Execute bonus-menu Huffman, reference and glyph paths in native MIPS."""
import json,re,struct
from unicorn import Uc,UC_ARCH_MIPS,UC_MODE_MIPS32,UC_MODE_LITTLE_ENDIAN,UC_HOOK_CODE
from unicorn.mips_const import *
from textcodec import ROOT
from bytelz import decompress
from korean_codec import raster

def main():
    r=json.loads((ROOT/'analysis/omake-insertion.json').read_text('utf8'))
    u=Uc(UC_ARCH_MIPS,UC_MODE_MIPS32|UC_MODE_LITTLE_ENDIAN);u.mem_map(0,0x200000)
    u.mem_write(0x38000,(ROOT/'work/extracted/SLPM_861.98').read_bytes()[0x800:])
    u.mem_write(0xc8000,(ROOT/'work/omake-patched.bin').read_bytes());symbols=r['symbols']
    stop=0x801fffc0
    def run(address,*args):
        u.reg_write(UC_MIPS_REG_SP,0x801ff000);u.reg_write(UC_MIPS_REG_RA,stop)
        for i,value in enumerate(args[:4]):u.reg_write(UC_MIPS_REG_A0+i,value)
        for i,value in enumerate(args[4:]):u.mem_write(0x1ff010+i*4,struct.pack('<I',value))
        u.emu_start(address,stop,count=300000)
        assert u.reg_read(UC_MIPS_REG_PC)==stop,hex(u.reg_read(UC_MIPS_REG_PC))
        assert u.reg_read(UC_MIPS_REG_SP)==0x801ff000
        return u.reg_read(UC_MIPS_REG_V0)
    for row in r['encoded']:
        pointer=run(symbols['kr_omake_get_text'],row['id']*4);raw=bytes.fromhex(row['raw_hex'])
        assert pointer==0x800ffb80 and bytes(u.mem_read(0xffb80,len(raw)))==raw,row['id']
        expected=max((sum(6 if c==' ' else 12 for c in line) for line in row['translation'].split('\n')),default=0)
        assert run(0x800e0d68,row['id'])==(expected+11)//12
    captured=[]
    def intercept(_u,address,size,data):
        pointer=u.reg_read(UC_MIPS_REG_A0)&0x1fffffff;raw=bytearray()
        while (b:=u.mem_read(pointer+len(raw),1)[0]):raw.append(b)
        captured.append((bytes(raw),u.reg_read(UC_MIPS_REG_A3)))
        u.reg_write(UC_MIPS_REG_V0,99);u.reg_write(UC_MIPS_REG_PC,u.reg_read(UC_MIPS_REG_RA))
    hook=u.hook_add(UC_HOOK_CODE,intercept,begin=0x800dc428,end=0x800dc428)
    for i,expected in enumerate(r['small_encoded']):
        source=bytes((1+(i>>7),0x80+(i&127),0));u.mem_write(0x1d0000,source)
        assert run(0x800dc420,0x801d0000,12,20,1,3,4)==99
        assert captured[-1][0]==bytes.fromhex(expected)[:-1],i
    # Mixed numeric output must retain ASCII digits around inline name refs.
    u.mem_write(0x1d0000,b'HP 123 '+bytes((1,0x80))+b' 999\0')
    run(0x800dc420,0x801d0000,0,0,4,0,0)
    assert captured[-1][0]==b'HP 123 '+bytes.fromhex(r['small_encoded'][0])[:-1]+b' 999'
    u.mem_write(0x1d0000,b'Original English 123\0');run(0x800dc420,0x801d0000,0,0,22,0,0)
    assert captured[-1]==(b'Original English 123',22)
    u.hook_del(hook)
    # Every kana-selector literal in the actual data section is now linked,
    # including the formerly omitted first 0x5e0 bytes and record labels.
    bank=json.loads((ROOT/'translations/omake-small.ko.json').read_text('utf8'))
    original=(ROOT/'work/decompressed/OMAKEDIR/OMAKE.PAC').read_bytes()
    covered={p for row in bank['records'] for p in range(row['offset'],row['offset']+row['length'])}
    missing=[m.start() for m in re.finditer(rb'%[kK][^\0]*',original[:0x32f0])
        if re.search(rb'[\xa1-\xdf]',m[0]) and m.start() not in covered]
    assert not missing,missing
    headings=[]
    def heading_call(cpu,address,size,data):
        headings.append(tuple(cpu.reg_read(reg) for reg in [UC_MIPS_REG_A0,UC_MIPS_REG_A1,UC_MIPS_REG_A2]))
        cpu.reg_write(UC_MIPS_REG_PC,cpu.reg_read(UC_MIPS_REG_RA))
    hook=u.hook_add(UC_HOOK_CODE,heading_call,begin=0x800da4ac,end=0x800da4ac)
    run(symbols['kr_omake_record_columns'],0,4,11,0x800cb094)
    assert headings==[(0,4,11),(0,7,11),(0,17,11),(0,21,11)],headings
    u.hook_del(hook)
    locations={i:r['small_locations'][c] for c,i in r['small_mapping'].items()}
    def uv(i):
        x,y=locations[i];return (x%256,y)
    cases=0
    for frame in [0,1]:
        u.mem_write(0xf9678,struct.pack('<I',0x801e1000));u.mem_write(0x1e1038,struct.pack('<I',frame))
        u.mem_write(0xf967c,struct.pack('<I',0x801e0000))
        for glyph in [0,62,63,125,126,len(r['small_mapping'])-1]:
            u.mem_write(0x1e0000,bytes(4));u.mem_write(0x1a0000,bytes(92))
            run(0x800dc210,40,50,0x1000+glyph,2,3,0x801a0000)
            sprite=bytes(u.mem_read(0x1a0000+24+frame*20,20))
            assert struct.unpack_from('<hh',sprite,8)==(40,50)
            assert sprite[12:14]==bytes(uv(glyph))
            assert sprite[3]==4 and sprite[7]&0xfc==0x64 and struct.unpack_from('<HH',sprite,16)==(7,8)
            assert struct.unpack('<H',u.mem_read(0x1e0002,2))[0]==1
            cases+=1
    for char in [32,65,0x80,0xff]:
      for border in [0,1]:
        for loop in [0,1]:
            u.mem_write(0xfff94,struct.pack('<I',border))
            u.mem_write(0x1d0000,bytes((char,)));u.reg_write(UC_MIPS_REG_S0,0x801d0001)
            u.reg_write(UC_MIPS_REG_S2,100);u.reg_write(UC_MIPS_REG_V0,loop)
            end=0x800dc494 if loop else 0x800dc4e8
            u.emu_start(symbols['kr_omake_small_advance_hook'],end,count=100)
            assert u.reg_read(UC_MIPS_REG_PC)==end
            assert u.reg_read(UC_MIPS_REG_S2)==100+(4 if char==32 and not border else 8)
    u.mem_write(0xfff94,bytes(4))
    # The formatted-text engine uses a separate packet path from window labels.
    u.mem_write(0xf4fc4,struct.pack('<I',0x801a0000))
    for i,expected in enumerate(r['small_encoded']):
        state=bytearray(0x9c);struct.pack_into('<HH',state,0x18,2,1)
        struct.pack_into('<HH',state,0x24,20,30)
        u.mem_write(0x1e0000,bytes(state));u.mem_write(0xfff8c,bytes(8))
        u.mem_write(0x1a0000,bytes(92*32));u.mem_write(0x1e1038,bytes(4))
        u.mem_write(0x1d0000,bytes((1+(i>>7),0x80+(i&127),0)))
        run(0x800d9d40,0x801d0000)
        raw=bytes.fromhex(expected);p=packet=0;x=36
        while raw[p]:
            c=raw[p];p+=1
            if c==32:x+=4;continue
            if 0x10<=c<=0x1f:
                glyph=((c-0x10)<<7)|(raw[p]&127);p+=1
                sprite=bytes(u.mem_read(0x1a0000+packet*92+24,20))
                assert sprite[12:14]==bytes(uv(glyph)),(i,packet)
            sprite=bytes(u.mem_read(0x1a0000+packet*92+24,20))
            assert struct.unpack_from('<hh',sprite,8)==(x,38),(i,packet,x,sprite.hex())
            x+=8;packet+=1
        assert struct.unpack('<H',u.mem_read(0x1e0002,2))[0]==packet
    captured_attributes=[]
    def attribute_glyph(_u,address,size,data):
        captured_attributes.append(u.reg_read(UC_MIPS_REG_A0))
        u.reg_write(UC_MIPS_REG_PC,u.reg_read(UC_MIPS_REG_RA))
    hook=u.hook_add(UC_HOOK_CODE,attribute_glyph,begin=0x800e0ad0,end=0x800e0ad0)
    for mask in range(1,256):
        captured_attributes.clear();run(0x800ccc78,24,200,mask)
        expected=[r['mapping'][c] for i,text in enumerate(['불','얼음','번개','독','물','땅','바람','성']) if mask&(1<<i) for c in text]
        assert captured_attributes==expected,mask
    u.hook_del(hook)
    # Big space consumes no packet and uses the same half-width advance.
    u.mem_write(0xf7de8,struct.pack('<H',100));run(0x800e0ad0,0)
    assert struct.unpack('<H',u.mem_read(0xf7de8,2))[0]==106
    old=decompress((ROOT/'work/extracted/OMAKEDIR/ALLTIM.BIN').read_bytes())[0]
    new=decompress((ROOT/'work/modified/OMAKEDIR/ALLTIM.BIN').read_bytes())[0]
    at=8+struct.unpack_from('<I',old,8)[0];size=struct.unpack_from('<I',old,at)[0]
    a,b=old[at+12:at+size],new[at+12:at+size]
    for y in range(256):
        assert a[y*512:y*512+128]==b[y*512:y*512+128]
        assert a[y*512+384:(y+1)*512]==b[y*512+384:(y+1)*512]
    pixels=bytes(c for v in b for c in (v&15,v>>4))
    for c,i in r['small_mapping'].items():
        g=raster(c,small=True);x,y=r['small_locations'][c]
        for yy in range(8):
            for xx in range(7):assert (pixels[(y+yy)*1024+x+xx]==3)==bool(g.getpixel((xx,yy)))
    for c,i in r['mapping'].items():
        if c in r['preserved_large_English']:continue
        g=raster(c);x=256+i//441*256+(i%441%21)*12;y=(i%441//21)*12
        for yy in range(12):
            for xx in range(12):assert (pixels[(y+yy)*1024+x+xx]==3)==bool(yy<g.height and g.getpixel((xx,yy)))
    result={'native_big_strings':len(r['encoded']),'native_small_references':len(r['small_encoded']),
        'kana_selector_literals_missing':len(missing),'record_panel_heading_columns':[4,7,17,21],
        'native_glyph_packet_cases':cases,'large_font':'Galmuri9','large_cell':[12,12],'small_font':'Galmuri7','small_cell':[8,8],'space_pixels':{'large':6,'small':4},'original_English_small_atlas':'preserved',
        'mixed_numeric_output':'passed','native_gameplay':'pending'}
    (ROOT/'analysis/omake-native-verification.json').write_text(json.dumps(result,indent=2)+'\n','utf8');print(result)

if __name__=='__main__':main()
