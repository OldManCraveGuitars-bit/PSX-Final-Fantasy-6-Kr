"""Run the actual MIPS decoder and original native battle text dispatcher."""
import json,struct
from unicorn import Uc,UC_ARCH_MIPS,UC_MODE_MIPS32,UC_MODE_LITTLE_ENDIAN,UC_HOOK_CODE
from unicorn.mips_const import *
from textcodec import ROOT
from korean_codec import font_index

def main():
    report=json.loads((ROOT/'analysis/battle-big-text-insertion.json').read_text('utf8'))
    small=json.loads((ROOT/'analysis/battle-small-runtime.json').read_text('utf8'))
    symbols=report['symbols'];u=Uc(UC_ARCH_MIPS,UC_MODE_MIPS32|UC_MODE_LITTLE_ENDIAN)
    u.mem_map(0,0x200000);u.mem_map(0x1f800000,0x1000)
    u.mem_write(0,(ROOT/'work/battle-native-original-memory/ram.bin').read_bytes())
    u.mem_write(0xc8000,(ROOT/'work/battle-overlay-small-names.bin').read_bytes())
    u.mem_write(0x197c00,(ROOT/'work/battle-korean-data.bin').read_bytes())
    u.mem_write(0x6c168,struct.pack('<I',0x1f8003c8))
    u.mem_write(0x6c16c,struct.pack('<I',0x1f8003ca))
    u.mem_write(0x6c1a0,struct.pack('<I',0x1f8003cc))
    def invoke(address,args=(),limit=500000):
        u.reg_write(UC_MIPS_REG_SP,0x801ff000);u.reg_write(UC_MIPS_REG_RA,0x801fffc0)
        for reg,v in zip([UC_MIPS_REG_A0,UC_MIPS_REG_A1,UC_MIPS_REG_A2,UC_MIPS_REG_A3],args):u.reg_write(reg,v)
        u.emu_start(address,0x801fffc0,count=limit)
        assert u.reg_read(UC_MIPS_REG_PC)==0x801fffc0,hex(u.reg_read(UC_MIPS_REG_PC))
        assert u.reg_read(UC_MIPS_REG_SP)==0x801ff000
    for row in report['encoded']:
        u.mem_write(0x1e0680,b'\xa5'*256)
        invoke(symbols['kr_big_expand'],[row['id'],0x801e0680])
        expected=bytes.fromhex(row['hex'])
        assert bytes(u.mem_read(0x1e0680,len(expected)))==expected,row['id']
    # Capture the glyph submitted to the original rasterizer; the original
    # control dispatcher and its double-byte handling execute unchanged.
    seen=[]
    relocation=report.get('digit_glyph_relocation')
    def physical(index):
        if relocation and relocation['original_first']<=index<relocation['original_first']+relocation['count']:
            return relocation['safe_first']+index-relocation['original_first']
        return index
    def code(uc,address,size,user):
        if address==symbols['kr_big_original_glyph']:
            seen.append(struct.unpack('<H',uc.mem_read(0x2e026,2))[0]//22)
            uc.reg_write(UC_MIPS_REG_PC,uc.reg_read(UC_MIPS_REG_RA))
        elif address==0x800cfcd8:
            uc.reg_write(UC_MIPS_REG_PC,uc.reg_read(UC_MIPS_REG_RA))
    u.hook_add(UC_HOOK_CODE,code)
    def indices(stream):
        out=[];p=0
        while stream[p]:
            c=stream[p];p+=1
            if 0x1c<=c<=0x1f:out.append(224+((c-0x1c)<<8)+stream[p]);p+=1
            elif c>=32:out.append(c-32)
            else:raise AssertionError(('Unexpected fixed-name control',c))
        return [physical(index) for index in out]
    for row in report['encoded'][:613]:
        identifier=row['id'];ref=bytes((0x18,identifier%255+1,identifier//255+1,0))
        u.mem_write(0x237d5,ref);u.mem_write(0x268a7,struct.pack('<HB',0x37d5,2));seen.clear()
        invoke(0x800cfbb4)
        assert seen==indices(bytes.fromhex(row['hex'])),(identifier,seen,indices(bytes.fromhex(row['hex'])))
    mapping={c:bytes.fromhex(v) for c,v in report['mapping'].items()}
    def expected_small(row):
        import re
        return [physical(font_index(mapping[c])) for c in re.sub(r'\{[^{}]+\}','',row['translation'])]
    tested=0
    for row in small['records']:
        route={'command':'kr_big_command','spell':'kr_big_attack','item':'kr_big_item'}.get(row['category'])
        if not route:continue
        u.mem_write(0x1f8003c8,struct.pack('<H',row['index']));seen.clear();invoke(symbols[route])
        assert seen==expected_small(row),(row['category'],row['index'],seen,expected_small(row))
        tested+=1
    # Widths are applied after both original font rendering branches.
    for idx,width in [(223,6),(0,12),(921,12)]:
        u.mem_write(0x2e07a,b'\x10');u.mem_write(0x2e026,struct.pack('<H',idx*22));invoke(symbols['kr_big_glyph'])
        assert u.mem_read(0x2e07a,1)[0]==16+width
    original_names=json.loads((ROOT/'analysis/fixed-catalog-original.json').read_text('utf8'))[:64]
    for row,name in zip(original_names,small['records'][:64]):
        u.mem_write(0x21000,bytes((2,row['index'])))
        u.mem_write(0x2e048,struct.pack('<HB',0x1000,2))
        u.mem_write(0x2f600,bytes((row['index'],0))+bytes.fromhex(row['original_hex']))
        seen.clear();invoke(symbols['kr_big_character'])
        assert seen==expected_small(name),(row['index'],seen,expected_small(name))
        assert bytes(u.mem_read(0x2e048,3))==bytes.fromhex('011002')
    u.mem_write(0x21000,b'\x02\0');u.mem_write(0x2e048,bytes.fromhex('001002'))
    u.mem_write(0x2f600,b'\0\0'+b'\xcb'*6);seen.clear();invoke(symbols['kr_big_character'])
    assert seen==[font_index(mapping['?'])]*6
    u.mem_write(0x2e048,bytes.fromhex('001002'));u.mem_write(0x2f602,bytes.fromhex('606162ffffff'))
    u.mem_write(0x36000,b'KRN1');u.mem_write(0x36010,struct.pack('<6H',ord('한'),32,ord('글'),0,0,0))
    u.mem_write(0x360d0,bytes(range(90)));seen.clear();invoke(symbols['kr_big_character'])
    assert seen==[930,223,930]
    assert bytes(u.mem_read(0x1d68f8+930*22,22))==bytes(range(60,82))
    # The real {string[00]} dispatcher uses the reward party slot. Its former
    # byte-to-glyph loop must never interpret Japanese bytes or cache tile IDs.
    reward_cases=0
    for party in range(4):
        address=0x20eae+party*32
        u.mem_write(0x20f38,bytes((party,)))
        for row,name in zip(original_names,small['records'][:64]):
            u.mem_write(0x2f600,b'\xff'*(37*16))
            raw=bytes.fromhex(row['original_hex'])
            slot=row['index']%16
            u.mem_write(0x2f600+slot*37,bytes((row['index'],0))+raw)
            u.mem_write(address,bytes((14,))+raw)
            u.mem_write(0x21000,bytes((0x12,0,0)))
            u.mem_write(0x2e048,struct.pack('<HB',0x1000,2))
            seen.clear();invoke(0x800d037c)
            assert seen==expected_small(name),(party,row['index'],seen,expected_small(name))
            assert bytes(u.mem_read(0x2e048,3))==bytes.fromhex('011002')
            reward_cases+=1
        u.mem_write(address,b'\0'+b'\xcb'*6);seen.clear();invoke(0x800d0680)
        assert seen==[font_index(mapping['?'])]*6
        for slot in range(16):
            first=0x60+slot*6
            raw=bytes((first,first+1,first+2,first+3,first+4,first+5))
            u.mem_write(address,b'\0'+raw)
            u.mem_write(0x36010+slot*12,'한 글A!?'.encode('utf-16le'))
            u.mem_write(0x360d0+slot*180,bytes(range(180)))
            u.mem_write(0x2e07a,b'\0');seen.clear();invoke(0x800d0680)
            assert seen==[930,223,930,930,930,930],(party,slot,seen)
            assert bytes(u.mem_read(0x2e07a,1))==b'\x42'
            reward_cases+=1
    result={'native_huffman_records':len(report['encoded']),'original_dispatch_name_records':613,
        'dynamic_small_to_large_names':tested,'battle_default_actor_names':64,'unknown_name_preserved':True,
        'reward_default_and_custom_name_cases':reward_cases,'reward_unknown_party_slots':4,
        'reward_native_string_dispatch_and_pointer':'passed',
        'custom_hangul_name':'한 글','space_pixels':6,'glyph_pixels':12,'native_gameplay_verification':'pending'}
    (ROOT/'analysis/battle-big-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n','utf8')
    print(result)
if __name__=='__main__':main()
