"""Run the saved-name producer, dispatcher, and all eight Bushido names."""
import json,struct
from unicorn import Uc,UC_ARCH_MIPS,UC_MODE_MIPS32,UC_MODE_LITTLE_ENDIAN,UC_HOOK_CODE
from unicorn.mips_const import *
from textcodec import ROOT
from pac import decompress

def main():
    old=json.loads((ROOT/'work/snapshots/v086-before-bushido-fix/analysis/battle-big-text-insertion.json').read_text('utf8'))
    new=json.loads((ROOT/'analysis/battle-big-text-insertion.json').read_text('utf8'))
    original=(ROOT/'work/extracted/BTL/FF6_BTL.BIN').read_bytes()[0x1fff8:0x20028]
    prior=(ROOT/'work/v086-cache-payloads/BTL/FF6_BTL.BIN').read_bytes()
    current=(ROOT/'work/battle-korean-data.bin').read_bytes()
    # Keep existing prefix scratch bytes unchanged; metadata follows the buffer.
    assert current[0x3bbc:0x3c00]==prior[0x3bbc:0x3c00]
    assert current[0x3c00+0x1e200:0x3c00+0x1e300]==prior[0x3c00+0x1e200:0x3c00+0x1e300]
    bonus=json.loads((ROOT/'translations/omake-manual.json').read_text('utf8'))
    results={}
    for tag,report,overlay,data in [
        ('v086',old,decompress((ROOT/'work/v086-cache-payloads/BTL/BATTLE.PAC').read_bytes())[0],(ROOT/'work/v086-cache-payloads/BTL/FF6_BTL.BIN').read_bytes()),
        ('v087',new,(ROOT/'work/battle-overlay-small-names.bin').read_bytes(),(ROOT/'work/battle-korean-data.bin').read_bytes())]:
        u=Uc(UC_ARCH_MIPS,UC_MODE_MIPS32|UC_MODE_LITTLE_ENDIAN)
        u.mem_map(0,0x200000);u.mem_map(0x1f800000,0x1000)
        u.mem_write(0,(ROOT/'work/battle-native-original-memory/ram.bin').read_bytes())
        u.mem_write(0xc8000,overlay);u.mem_write(0x197c00,data)
        for ptr,val in [(0x6c168,0x1f8003c8),(0x6c16c,0x1f8003ca),(0x6c1a0,0x1f8003cc),(0x6c1d8,0x1f8003d4)]:u.mem_write(ptr,struct.pack('<I',val))
        producing=False;seen=[]
        def hook(uc,at,size,user):
            if producing and at==0x80127794:uc.emu_stop()
            elif at==report['symbols']['kr_big_original_glyph']:
                seen.append(struct.unpack('<H',uc.mem_read(0x2e026,2))[0]//22)
                uc.reg_write(UC_MIPS_REG_PC,uc.reg_read(UC_MIPS_REG_RA))
            elif at==0x800cfcd8:uc.reg_write(UC_MIPS_REG_PC,uc.reg_read(UC_MIPS_REG_RA))
        u.hook_add(UC_HOOK_CODE,hook)
        def produce(index,saved):
            nonlocal producing
            u.mem_write(0x2fcf8,saved);u.mem_write(0x237d4,b'\xa5'*20)
            u.mem_write(0x1ff012,struct.pack('<H',index*6));u.mem_write(0x1f8003ca,b'\0\0')
            u.reg_write(UC_MIPS_REG_SP,0x801ff000);producing=True
            u.emu_start(0x801275b4,0x801fffc0,count=100000);producing=False
            assert u.reg_read(UC_MIPS_REG_PC)==0x80127794
            assert u.reg_read(UC_MIPS_REG_SP)==0x801ff000
            assert bytes(u.mem_read(0x2fcf8,48))==saved
            return bytes(u.mem_read(0x237d5,13))
        records=[]
        for index in range(8):
            got=produce(index,original)
            text=bonus[str(570+index)]
            stream=b''.join(bytes.fromhex(new['mapping'][c]) for c in text)+b'\0';expected=[];p=0
            while stream[p]:
                c=stream[p];p+=1
                if 0x1c<=c<=0x1f:idx=224+(c-0x1c)*256+stream[p];p+=1
                else:idx=c-32
                expected.append(idx)
            if tag=='v087':
                assert got[:len(stream)]==stream
                assert got[len(stream):]==b'\xa5'*(13-len(stream))
            u.mem_write(0x268a7,struct.pack('<HB',0x37d5,2));u.mem_write(0x2e07a,b'\0')
            u.reg_write(UC_MIPS_REG_RA,0x801fffc0);seen.clear()
            u.emu_start(0x800cfbb4,0x801fffc0,count=500000)
            assert u.reg_read(UC_MIPS_REG_PC)==0x801fffc0
            matched=seen==expected
            if tag=='v087':assert matched,(index,seen,expected)
            else:assert not matched
            assert bytes(u.mem_read(0x237d4,1))==b'\xa5'
            assert bytes(u.mem_read(0x237e2,6))==b'\xa5'*6
            records.append({'level':index+1,'text':text,'glyphs_match':matched,'width_pixels':u.mem_read(0x2e07a,1)[0]})
        # Every editable saved byte uses the same Korean glyph in battle.
        custom_cases=0
        if tag=='v087':
            chars=json.loads((ROOT/'translations/swdtech-characters.ko.json').read_text('utf8'))
            for c in range(256):
                saved=bytes((c,))*6+original[6:];got=produce(0,saved)
                text=chars.get(str(c),{'translation':' '})['translation']
                expected=bytes.fromhex(new['mapping'][text])*6+b'\0' if c!=255 else b'\0'
                assert got[:len(expected)]==expected,(c,got.hex(),expected.hex())
                assert got[len(expected):]==b'\xa5'*(13-len(expected))
                u.mem_write(0x268a7,struct.pack('<HB',0x37d5,2));u.mem_write(0x2e07a,b'\0')
                u.reg_write(UC_MIPS_REG_RA,0x801fffc0);seen.clear()
                u.emu_start(0x800cfbb4,0x801fffc0,count=500000)
                assert u.reg_read(UC_MIPS_REG_PC)==0x801fffc0
                assert len(seen)==(0 if c==255 else 6),(c,seen)
                custom_cases+=1
            # Deleting a middle slot must agree with the menu. Only EF is a
            # selectable space; FF is padding even when followed by letters.
            saved=bytes.fromhex('80ffef90ffff')+original[6:]
            got=produce(0,saved)
            expected=b''.join(bytes.fromhex(new['mapping'][chars[str(c)]['translation']]) for c in [128,239,144])+b'\0'
            assert got[:len(expected)]==expected
            assert got[len(expected):]==b'\xa5'*(13-len(expected))
        results[tag]={'default_names':records,'custom_character_cases':custom_cases,'middle_padding_matches_menu':tag=='v087','saved_names_unchanged':True,'output_canaries':True,'native_status_window_region_preserved':True}
    (ROOT/'analysis/v087-bushido-name-verification.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n','utf8')
    print(json.dumps(results,ensure_ascii=False))

if __name__=='__main__':main()
