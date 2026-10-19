"""Execute default/custom name expansion and verify preserved English glyphs."""
import json,struct
from unicorn import Uc,UC_ARCH_MIPS,UC_MODE_MIPS32,UC_MODE_LITTLE_ENDIAN
from unicorn.mips_const import *
from textcodec import ROOT
from korean_codec import encode,fixed_relocations,font_index
from field_names import default_names
from pac import decompress

def main():
    u=Uc(UC_ARCH_MIPS,UC_MODE_MIPS32|UC_MODE_LITTLE_ENDIAN);u.mem_map(0,0x200000)
    u.mem_write(0xc8000,decompress((ROOT/'work/modified/NAR/NARITA.PAC').read_bytes())[0])
    nar=(ROOT/'work/modified/NAR/NAR_BIN.BIN').read_bytes();u.mem_write(0x130000,nar)
    metadata=json.loads((ROOT/'work/korean_encoding.json').read_text('utf8'))
    mapping={k:bytes.fromhex(v) for k,v in metadata['mapping'].items()}
    assigned={k:bytes.fromhex(v) for k,v in metadata['replaced'].items()}
    sources=json.loads((ROOT/'analysis/fixed-catalog-original.json').read_text('utf8'))[:64]
    names=default_names()
    preserved=[UC_MIPS_REG_A0,UC_MIPS_REG_A1,UC_MIPS_REG_A2,UC_MIPS_REG_A3,UC_MIPS_REG_V1,
        UC_MIPS_REG_T0,UC_MIPS_REG_T1,UC_MIPS_REG_T2,UC_MIPS_REG_T3,UC_MIPS_REG_T4,
        UC_MIPS_REG_T5,UC_MIPS_REG_T6,UC_MIPS_REG_T7,UC_MIPS_REG_T8,UC_MIPS_REG_T9,
        UC_MIPS_REG_S1,UC_MIPS_REG_S2,UC_MIPS_REG_RA]
    def run(slot,style):
        u.mem_write(0x1ff010,bytes((slot+(2 if style=='hchar' else 0xf0),0)))
        for i,reg in enumerate(preserved):u.reg_write(reg,0x1000+i*17)
        before={reg:u.reg_read(reg) for reg in preserved}
        u.reg_write(UC_MIPS_REG_SP,0x801ff000)
        u.emu_start(0x80102d78 if style=='hchar' else 0x80102ea4,0x801029cc,count=20000)
        assert u.reg_read(UC_MIPS_REG_PC)==0x801029cc
        for reg,value in before.items():assert u.reg_read(reg)==value,(reg,hex(value),hex(u.reg_read(reg)))
        assert u.reg_read(UC_MIPS_REG_SP)==0x801ff000
        return bytes(u.mem_read(0x27183,13)).split(b'\0',1)[0]
    cases=0
    # Decode by byte length, since a double-byte glyph can contain a zero byte.
    for row,text in zip(sources,names):
        u.mem_write(0x2f600,bytes((row['index'],)))
        u.mem_write(0x2f602,bytes.fromhex(row['original_hex']))
        expected=encode(text,mapping)
        for style in ['hchar','char']:
            run(0,style)
            assert bytes(u.mem_read(0x27183,len(expected)+1))==expected+b'\0',(row['index'],style,text)
            cases+=1
    u.mem_write(0x2f600,b'\0\0'+b'\xcb'*6)
    for style in ['hchar','char']:
        run(0,style)
        assert bytes(u.mem_read(0x27183,13))==encode('??????',mapping)+b'\0'
    fontdata=(ROOT/'work/korean-name-fonts.bin').read_bytes()
    u.mem_write(0x30700,b'KRN1');unicode=[ord('한'),32,ord('글')]
    u.mem_write(0x2f602,bytes.fromhex('606162ffffff'))
    u.mem_write(0x30710,struct.pack('<6H',*unicode,0,0,0))
    expected_glyphs=[]
    for i,c in enumerate(unicode):
        if c==32:record=bytes(30)
        else:
            n=c-0xac00;offset=struct.unpack_from('<I',fontdata,24+(n>>8)*8)[0]
            block=decompress(fontdata[offset:])[0];record=block[(n&255)*30:(n&255)*30+30]
        u.mem_write(0x307d0+i*30,record);expected_glyphs.append(record[:22])
    for style in ['hchar','char']:
        run(0,style)
        assert bytes(u.mem_read(0x27183,6))==bytes.fromhex('1fa0ff1fa200')
        for i in [0,2]:assert bytes(u.mem_read(0x194bd0+(1152+i)*22,22))==expected_glyphs[i]
    original=(ROOT/'work/extracted/NAR/NAR_BIN.BIN').read_bytes()
    moved=fixed_relocations(mapping,assigned)
    for _,old,new in moved:
        src=0x64bd0+font_index(old)*22;dest=0x64bd0+font_index(new)*22
        assert nar[dest:dest+22]==original[src:src+22]
        assert nar[0x646d0+font_index(new)+32]==original[0x646d0+font_index(old)+32]
    result={'default_name_expansions_passed':cases,'custom_name':'한 글','custom_name_styles':2,
        'unknown_name_styles_preserved':2,
        'half_width_space':'preserved','cached_large_glyphs':'matched',
        'original_English_and_punctuation_glyph_relocations_preserved':len(moved),
        'caller_registers_and_stack':'preserved'}
    (ROOT/'analysis/field-name-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n','utf8')
    print(result)

if __name__=='__main__':main()
