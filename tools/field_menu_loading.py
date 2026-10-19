"""Lossless full field reload; retain native VRAM restoration and PAC decoder."""
import json,struct,subprocess
import lz4.block
from textcodec import ROOT
from movie_subtitles import FONT_FILE_OFFSET,MOVIES,msf_word

PACK_OFFSET=0x40000

def prepare(changes,menu_lba,texture_mirror_lba):
    changes=dict(changes)
    previous_report=ROOT/'analysis/field-menu-loading.json'
    previous_symbols=json.loads(previous_report.read_text('utf8'))['symbols'] if previous_report.exists() else {}
    def sector_payload(path):
        data=changes[path]
        # All three original files have verified zero sector padding.
        inv=json.loads((ROOT/'analysis/disc_inventory.json').read_text('utf8'))
        entry=next(e for e in inv['entries'] if e['path']==path)
        with open(inv['source']['track_path'],'rb') as source:
            source.seek((entry['extent_lba']+(entry['size']//2048))*2352+24+entry['size']%2048)
            tail=source.read((-entry['size'])%2048)
        assert not any(tail)
        return data+bytes((-len(data))%2048)
    field=sector_payload('NAR/NAR_BIN.BIN')
    script=sector_payload('NAR/NAR_BIN3.BIN')
    overlay=sector_payload('NAR/NARITA.PAC')
    assert len(field)==0x9b800 and len(script)==0x20000 and len(overlay)==0x22800
    pack=lambda d:lz4.block.compress(d,mode='high_compression',compression=12,store_size=True)
    first=pack(field)
    second=pack(script)
    assert lz4.block.decompress(first)==field and lz4.block.decompress(second)==script
    first+=bytes((-len(first))%2048)
    # First read fits BELOW its decoded output, without touching live records.
    assert 0xc8000+len(first)<=0x130000
    # Sector-align the script stream, immediately followed by native PAC.
    # After the queued read completes, a backward move restores the PAC's
    # original buffer at 10D800 without any unread-input overlap.
    second+=bytes((-len(second))%2048)
    pac_source=0x800e8000+len(second)
    second+=overlay
    assert 0xe8000+len(second)<=0x130000
    msf1=msf_word(menu_lba+PACK_OFFSET//2048)
    msf2=msf_word(menu_lba+(PACK_OFFSET+len(first))//2048)
    texture_original_msf=msf_word(1022)
    texture_near_msf=msf_word(texture_mirror_lba)
    tool=ROOT/'references/psx-toolchain/bin';elf=ROOT/'work/menu-lz4.elf'
    subprocess.run([str(tool/'mipsel-none-elf-gcc.exe'),'-march=r3000','-mabi=32','-mno-abicalls','-fno-pic','-G0','-nostdlib',
        f'-DFIELD_BIN_PACKED_SIZE={len(first)}',f'-DFIELD_TAIL_PACKED_SIZE={len(second)}',f'-DFIELD_BIN_MSF={msf1}',f'-DFIELD_TAIL_MSF={msf2}',
        f'-DFIELD_TEXTURE_ORIGINAL_MSF={texture_original_msf}',f'-DFIELD_TEXTURE_NEAR_MSF={texture_near_msf}',
        f'-Wl,-T{ROOT.as_posix()}/native/menu-lz4.ld,--build-id=none','-o',str(elf),
        str(ROOT/'native/menu_lz4.S'),str(ROOT/'native/field_menu_loading.S')],check=True)
    subprocess.run([str(tool/'mipsel-none-elf-objcopy.exe'),'-O','binary',str(elf),str(ROOT/'work/menu-lz4.bin')],check=True)
    code=(ROOT/'work/menu-lz4.bin').read_bytes()
    assert len(code)<=0x180,('Resident loader allocation overflow',len(code))
    symbols={}
    for line in subprocess.check_output([str(tool/'mipsel-none-elf-nm.exe'),'-n',str(elf)],text=True).splitlines():
        f=line.split()
        if len(f)==3:symbols[f[2]]=int(f[0],16)&0xffffffff
    exe=bytearray(changes['SLPM_861.98']);base=struct.unpack_from('<I',exe,0x18)[0]
    at=0x80037680-base+0x800
    exe[at:at+0x180]=code+bytes(0x180-len(code))
    at=0x8003a4a8-base+0x800;hook=(2<<26)|((symbols['kr_field_menu_return']>>2)&0x3ffffff)
    assert struct.unpack_from('<I',exe,at)[0] in (0x8f840338,hook)
    struct.pack_into('<II',exe,at,hook,0)
    at=0x8003a604-base+0x800
    deferred=(2<<26)|((symbols['kr_field_menu_after_wait']>>2)&0x3ffffff)
    old_deferred=(2<<26)|((previous_symbols.get('kr_field_menu_after_wait',symbols['kr_field_menu_after_wait'])>>2)&0x3ffffff)
    assert struct.unpack_from('<II',exe,at) in ((0x34020003,0),(deferred,0),(old_deferred,0))
    struct.pack_into('<II',exe,at,deferred,0)
    # The replaced default read block is dead after its unconditional hook.
    # Keep the adjacent mode-1 and mode-2 entry points byte-identical.
    end=pac_source+len(overlay)
    move=[0x3c080000|(end>>16),0x35080000|(end&65535),0x3c098013,
          0x3c0a0000|(pac_source>>16),0x354a0000|(pac_source&65535),
          0x8d0bfffc,0x2508fffc,0xad2bfffc,0x150afffc,0x2529fffc,
          0x0800e984,0x34040200]
    at=0x8003a4b0-base+0x800;exe[at:at+48]=struct.pack('<12I',*move)
    # Discard the earlier experimental distant banks. The final banks live
    # beside the menu; the original executable/caption extent is sufficient.
    del exe[FONT_FILE_OFFSET+len(MOVIES)*4096:]
    changes['SLPM_861.98']=bytes(exe)
    report=dict(first_read_bytes=len(first),second_read_bytes=len(second),
        previous_full_read_bytes=0x9b800+0x20000+0x22800,
        decoded_field_bytes=len(field),decoded_script_bytes=len(script),
        first_source='0x800c8000',first_destination='0x80130000',
        second_source='0x800e8000',second_destination='0x800c8000',
        native_PAC_source='0x8010d800',native_VRAM_restoration_preserved=True,
        queued_second_read=True,PAC_transient_source=hex(pac_source),PAC_transient_end=hex(end),
        bank_container='HAR/MENUMENU.BIN',bank_offset=PACK_OFFSET,bank_MSFs=[msf1,msf2],
        texture_mirror_lba=texture_mirror_lba,texture_original_lba=1022,
        texture_MSFs=[texture_original_msf,texture_near_msf],
        texture_route_restored_on_partial_return=True,
        resident_loader_bytes=len(code),symbols=symbols,
        hook='0x8003a4a8',continuation='0x8003a5a4',partial_load_paths_preserved=True)
    (ROOT/'work/field-menu-read1.bin').write_bytes(first)
    (ROOT/'work/field-menu-read2.bin').write_bytes(second)
    (ROOT/'analysis/field-menu-loading.json').write_text(json.dumps(report,indent=2)+'\n','utf8')
    return changes,report,first+second
