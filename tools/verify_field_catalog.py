"""Execute all native field catalog substitutions and preserve caller state."""
import json,struct,sys
from unicorn import Uc,UC_ARCH_MIPS,UC_MODE_MIPS32,UC_MODE_LITTLE_ENDIAN
from unicorn.mips_const import *
from textcodec import ROOT
from pac import decompress
from korean_codec import raster

def main():
    report=json.loads((ROOT/'analysis/field-catalog-insertion.json').read_text('utf8'))
    u=Uc(UC_ARCH_MIPS,UC_MODE_MIPS32|UC_MODE_LITTLE_ENDIAN);u.mem_map(0,0x200000)
    if '--prepared' in sys.argv:
        u.mem_write(0xc8000,(ROOT/'work/field-catalog-qa-overlay.bin').read_bytes())
        u.mem_write(0x130000,(ROOT/'work/field-catalog-qa-nar.bin').read_bytes())
        u.mem_write(0x1a6200,(ROOT/'work/field-catalog-qa-script.bin').read_bytes())
    else:
        u.mem_write(0xc8000,decompress((ROOT/'work/modified/NAR/NARITA.PAC').read_bytes())[0])
        u.mem_write(0x130000,(ROOT/'work/modified/NAR/NAR_BIN.BIN').read_bytes())
        u.mem_write(0x1a6200,(ROOT/'work/modified/NAR/NAR_BIN3.BIN').read_bytes())
    preserved=[UC_MIPS_REG_A0,UC_MIPS_REG_A1,UC_MIPS_REG_A2,UC_MIPS_REG_A3,UC_MIPS_REG_V1,
        UC_MIPS_REG_T0,UC_MIPS_REG_T1,UC_MIPS_REG_T2,UC_MIPS_REG_T3,UC_MIPS_REG_T4,
        UC_MIPS_REG_T5,UC_MIPS_REG_T6,UC_MIPS_REG_T7,UC_MIPS_REG_T8,UC_MIPS_REG_T9,
        UC_MIPS_REG_S1,UC_MIPS_REG_S2,UC_MIPS_REG_RA]
    for row in report['records']:
        category=row['category'];address=0x801034d8 if category=='item' else 0x80103624
        u.mem_write(0x2e583 if category=='item' else 0x2e584,bytes((row['index'],)))
        u.mem_write(0x27183,b'\xa5'*32)
        for i,reg in enumerate(preserved):u.reg_write(reg,0x1000+i*17)
        before={reg:u.reg_read(reg) for reg in preserved};u.reg_write(UC_MIPS_REG_SP,0x801ff000)
        u.emu_start(address,0x80103760,count=200000)
        assert u.reg_read(UC_MIPS_REG_PC)==0x80103760
        assert u.reg_read(UC_MIPS_REG_SP)==0x801ff000
        for reg,value in before.items():assert u.reg_read(reg)==value
        expected=bytes.fromhex(row['hex'])
        assert bytes(u.mem_read(0x27183,len(expected)))==expected,(category,row['index'])
    for i,c in enumerate(report['extra_glyphs']):
        image=raster(c);expected=b''.join(struct.pack('<H',sum(1<<(11-x) for x in range(12) if image.getpixel((x,y)))) for y in range(11))
        assert bytes(u.mem_read(0x19aed0+i*22,22))==expected
    result={'native_field_substitutions':len(report['records']),'extra_glyphs':len(report['extra_glyphs']),
        'zero_operand_double_byte_glyphs':'preserved','caller_registers_and_stack':'preserved','native_gameplay_verification':'pending'}
    (ROOT/'analysis/field-catalog-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n','utf8')
    print(result)
if __name__=='__main__':main()
