"""Execute controller input, font generation and the native save payload copies."""
import json,struct,sys
from unicorn import Uc,UC_ARCH_MIPS,UC_MODE_MIPS32,UC_MODE_LITTLE_ENDIAN,UC_HOOK_CODE
from unicorn.mips_const import *
from textcodec import ROOT
from pac import decompress

def main():
    field_cache='--field-cache' in sys.argv
    symbols=json.loads((ROOT/'analysis/v081-field-cache.json').read_text('utf8'))['menu_symbols'] if field_cache else json.loads((ROOT/'analysis/small-runtime.json').read_text('utf8'))['symbols']
    payloads=ROOT/('work/v081-cache-payloads' if field_cache else 'work/modified')
    u=Uc(UC_ARCH_MIPS,UC_MODE_MIPS32|UC_MODE_LITTLE_ENDIAN);u.mem_map(0,0x200000)
    u.mem_write(0,(ROOT/'work/v009-galmuri7-menu-memory/ram.bin').read_bytes())
    u.mem_write(0xc8000,decompress((payloads/'HAR/HARATA.PAC').read_bytes())[0])
    u.mem_write(0x140000,(payloads/'HAR/MENUMENU.BIN').read_bytes())
    uploads=[]
    def mock(_uc,address,_size,_data):
        if address==0x800543ac:
            args=[u.reg_read(r)&0x1fffff for r in (UC_MIPS_REG_A0,UC_MIPS_REG_A1)]
            u.mem_write(args[0],bytes(u.mem_read(args[1],u.reg_read(UC_MIPS_REG_A2))))
        if address==0x8003af2c:
            assert field_cache and u.reg_read(UC_MIPS_REG_A1)==0x80172000
            data=(ROOT/'work/korean-name-fonts.bin').read_bytes();size=u.reg_read(UC_MIPS_REG_A3)
            u.mem_write(0x172000,data+bytes(size-len(data)))
        if address==0x8005adb8:
            ptr=u.reg_read(UC_MIPS_REG_A0)&0x1fffffff
            uploads.append(struct.unpack('<4h',u.mem_read(ptr,8)))
        u.reg_write(UC_MIPS_REG_V0,0);u.reg_write(UC_MIPS_REG_PC,u.reg_read(UC_MIPS_REG_RA))
    for addr in [0x8005adb8,0x8005ab0c,0x800d83f8,0x800fca90,0x800fcb44,0x800fcb08,*([0x800543ac,0x8003af2c] if field_cache else [])]:
        u.hook_add(UC_HOOK_CODE,mock,begin=addr,end=addr)
    def call(name,a1=0):
        u.reg_write(UC_MIPS_REG_SP,0x801ff000);u.reg_write(UC_MIPS_REG_RA,0x801fffc0)
        u.reg_write(UC_MIPS_REG_A0,0x80193000);u.reg_write(UC_MIPS_REG_A1,a1)
        u.emu_start(symbols[name],0x801fffc0,count=5000000)
        assert u.reg_read(UC_MIPS_REG_PC)==0x801fffc0,(name,'did not return')
        return u.reg_read(UC_MIPS_REG_V0)
    def text():
        count=call('hn_text',0x801e1000)
        return bytes(u.mem_read(0x1e1000,count*2)).decode('utf-16le')
    def key(low,high,index=0):
        u.mem_write(0x2e008,bytes((low,high)));u.mem_write(0x2e04a,bytes((0,index)))
        call('kr_name_keys')
    # Opening settings before the story's naming event must neither reveal
    # Tina's name nor rewrite empty actor records. Check both cache states.
    empty=b'\xff'+bytes(36)
    u.mem_write(0x2f600,empty*16)
    u.mem_write(0x30700,bytes(3088));u.mem_write(0x36000,bytes(3088))
    u.mem_write(0x2f600,b'\0\0'+b'\xcb'*6)
    unknown_calls=[]
    for _ in range(2):
        before=len(uploads);call('kr_names_menu_init');unknown_calls.append(len(uploads)-before)
        assert bytes(u.mem_read(0x2f602,6))==b'\xcb'*6
        assert bytes(u.mem_read(0x2f600+37,37*15))==empty*15
    assert unknown_calls==[0,0],unknown_calls
    u.mem_write(0x2e067,bytes.fromhex('00f6'));call('kr_name_begin')
    assert text()=='티나','The actual naming event must still offer the default name'
    # Fresh cache, with Tina selected and an original Japanese name in WRAM.
    u.mem_write(0x30700,bytes(3088));u.mem_write(0x36000,bytes(3088));u.mem_write(0x2f600,bytes((0,0)))
    u.mem_write(0x2f602,bytes.fromhex('84c692ffffff'))
    call('kr_names_menu_init')
    assert bytes(u.mem_read(0x30710,4)).decode('utf-16le')=='티나'
    u.mem_write(0x2e067,bytes.fromhex('00f6'));call('kr_name_begin')
    assert text()=='티나'
    for expected in ['티ㄴ','티','ㅌ','']:
        key(0,0x80);assert text()==expected,(text(),expected)
    keys=json.loads((ROOT/'analysis/small-runtime.json').read_text('utf8'))['name_grid_keys']
    for c,expected in zip('ㅎㅏㄴㄱㅡㄹ',['ㅎ','하','한','한ㄱ','한그','한글']):
        key(0x80,0,keys.index(c));assert text()==expected,(text(),expected)
    key(0,0x10)
    assert bytes(u.mem_read(0x30710,4)).decode('utf-16le')=='한글'
    assert bytes(u.mem_read(0x2f602,6))==bytes.fromhex('6061ffffffff')
    fonts=(ROOT/'work/korean-name-fonts.bin').read_bytes()
    for i,c in enumerate('한글'):
        n=ord(c)-0xac00;offset=struct.unpack_from('<I',fonts,24+(n>>8)*8)[0]
        block=decompress(fonts[offset:])[0];expected=block[(n&255)*30:(n&255)*30+30]
        assert bytes(u.mem_read(0x307d0+i*30,30))==expected,(c,'glyph mismatch')
    cache=bytes(u.mem_read(0x36000,3088))
    assert bytes(u.mem_read(0x30700,3088))==cache
    checksum=0
    for value in cache[16:]:checksum=(((checksum<<1)|(checksum>>15))^value)&65535
    assert struct.unpack_from('<H',cache,6)[0]==checksum
    assert checksum!=65535,'Checksum must retain changes after long names and glyphs'
    # Run the two real DEO data-copy loops used around memory-card save/load.
    deo=decompress((ROOT/'work/extracted/DEODIR/DEO.PAC').read_bytes())[0]
    u.mem_write(0xc8000,deo)
    for reg,val in [(UC_MIPS_REG_A2,0x8002f600),(UC_MIPS_REG_A3,0x80034402),(UC_MIPS_REG_T0,0x80031400)]:u.reg_write(reg,val)
    u.emu_start(0x800da0b0,0x800da0fc,count=15000)
    payload=bytes(u.mem_read(0x34402,0x1e00))
    assert payload[0x1100:0x1100+3088]==cache
    u.mem_write(0x32400,payload+bytes(512));u.mem_write(0x30700,bytes(3088))
    for reg,val in [(UC_MIPS_REG_A2,0x80032400),(UC_MIPS_REG_A3,0x8002f600),(UC_MIPS_REG_T0,0x80034400)]:u.reg_write(reg,val)
    u.emu_start(0x800d543c,0x800d5468,count=15000)
    assert bytes(u.mem_read(0x30700,3088))==cache,'Native load did not restore the name cache'
    assert bytes(u.mem_read(0x2f602,6))==bytes.fromhex('6061ffffffff')
    result={'controller_sequence':'티나 → 한글','composition_and_granular_backspace':'passed',
        'unknown_name_preserved_on_menu_open':True,'empty_actor_records_preserved':15,
        'unknown_only_menu_name_uploads':unknown_calls,'naming_event_default':'티나',
        'font_generation':'matched decompressed Galmuri resources','save_payload_bytes':0x1e00,
        'cache_bytes':len(cache),'native_save_load_payload_roundtrip':'passed','gpu_upload_calls':len(uploads),
        'physical_memory_card_roundtrip':'pending','field_dialogue_name_expansion':'verified separately'}
    (ROOT/'analysis'/('v081-native-name-editor-verification.json' if field_cache else 'native-name-editor-verification.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n','utf8')
    print(result)

if __name__=='__main__':main()
