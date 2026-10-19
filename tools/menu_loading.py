"""Lossless on-disc menu packing with adjacent overlay/data extents.

work/modified keeps the decoded menu for renderer tests and editors. Only the
image payload is compressed; the executable and ISO both use the same routes.
Build dependency: python -m pip install lz4
"""
import json,struct
import lz4.block
from textcodec import ROOT
from pac import compress,decompress
from small_runtime import MENU_READ_SIZE
from movie_subtitles import msf_word

RESERVE_LBA=114063

def prepare(changes):
    changes=dict(changes)
    syms=json.loads((ROOT/'analysis/movie-subtitles-runtime.json').read_text('utf8'))['symbols']
    read_target=(3<<26)|((syms['kr_menu_read']>>2)&0x3ffffff)
    cached_target=(3<<26)|((syms['kr_menu_cached']>>2)&0x3ffffff)
    overlay=bytearray(decompress(changes['HAR/HARATA.PAC'])[0])
    menu=changes['HAR/MENUMENU.BIN']
    assert len(menu)==0x68000 and not any(menu[MENU_READ_SIZE:])
    packed=lz4.block.compress(menu[:MENU_READ_SIZE],mode='high_compression',compression=12,store_size=True)
    assert lz4.block.decompress(packed)==menu[:MENU_READ_SIZE]
    menu_sectors_bytes=(len(packed)+2047)&~2047
    jobs=(ROOT/'work/extracted/HAR/JOBOBJ.BIN').read_bytes()
    assert len(jobs)==0x2000
    # The native job-sprite read incurred a second seek after menu setup.
    # Keep the exact resource beside the cached menu and copy it at the same
    # original call site, after all earlier initializers have completed.
    job_source=0x801ac800+menu_sectors_bytes
    job_copy=[0x3c04800b,0x34841be8,0x3c050000|(job_source>>16),
              0x34a50000|(job_source&65535),0x080150eb,0x34062000]
    at=0x80110c7c-0x800c8000
    assert overlay[at:at+4]==struct.pack('<I',0x27bdffe0) or overlay[at:at+24]==struct.pack('<6I',*job_copy)
    overlay[at:at+24]=struct.pack('<6I',*job_copy)
    for address in (0x80108eac,0x8010f988):
        at=address-0x800c8000
        target=cached_target
        assert struct.unpack_from('<I',overlay,at)[0] in (0x0c00ebcb,read_target,cached_target)
        struct.pack_into('<I',overlay,at,target)
    packed_overlay=compress(bytes(overlay))
    assert len(packed_overlay)<=len(changes['HAR/HARATA.PAC'])
    changes['HAR/HARATA.PAC']=packed_overlay+bytes(len(changes['HAR/HARATA.PAC'])-len(packed_overlay))
    read_bytes=menu_sectors_bytes+len(jobs)
    # Do not reach system records or music; decompression must not overwrite
    # unread input. The output ends exactly at the staging buffer's beginning.
    assert 0x140000+MENU_READ_SIZE==0x1a0000
    assert 0x1a0000+read_bytes<=0x1e5000
    overlay_sectors=(len(changes['HAR/HARATA.PAC'])+2047)//2048
    assert overlay_sectors*2048==0x24800
    combined_bytes=overlay_sectors*2048+read_bytes
    assert 0x188000+combined_bytes<=0x1e5000
    assert overlay_sectors+read_bytes//2048<=256
    routes={'HAR/HARATA.PAC':{'reserve':'DUMMY0.DAT','sector_offset':0},
        'HAR/MENUMENU.BIN':{'reserve':'DUMMY0.DAT','sector_offset':overlay_sectors},
        'NAR/NAR_BIN2.BIN':{'reserve':'DUMMY0.DAT','sector_offset':544},
        'OMAKEDIR/OMAKE.PAC':{'reserve':'DUMMY0.DAT','sector_offset':1024}}
    # Keep the original physical extent intact for native partial field loads.
    # Only full menu returns select this byte-identical texture mirror.
    changes['NAR/NAR_BIN2.BIN']=(ROOT/'work/extracted/NAR/NAR_BIN2.BIN').read_bytes()
    assert 544+(len(changes['NAR/NAR_BIN2.BIN'])+2047)//2048<=1024
    exe=bytearray(changes['SLPM_861.98'])
    prefix=0x80038000-struct.unpack_from('<I',exe,0x18)[0]
    assert prefix==0x1800
    # The save-card return also reloads HARATA immediately before this call.
    # Use the already staged menu here too: a second read at 801a0000 would
    # overwrite the cached stream that the following menu init needs again.
    at=prefix+0x8003a1fc-0x80038000+0x800
    assert struct.unpack_from('<I',exe,at)[0] in (read_target,cached_target)
    struct.pack_into('<I',exe,at,cached_target)
    at=prefix+0x1f3c
    hi,lo=struct.unpack_from('<II',exe,at)
    assert hi>>16==0x3c09 and lo>>16==0x3529
    struct.pack_into('<II',exe,at,0x3c090000|(read_bytes>>16),0x35290000|(read_bytes&65535))
    at=prefix+0x1f34
    hi,lo=struct.unpack_from('<II',exe,at)
    assert hi>>16==0x3c08 and lo>>16==0x3508
    struct.pack_into('<II',exe,at,0x3c080000|(combined_bytes>>16),0x35080000|(combined_bytes&65535))
    assert struct.unpack_from('<II',exe,prefix+0x1f94) in ((0x3c198011,0x3739b800),(0x3c198018,0x37398000))
    struct.pack_into('<II',exe,prefix+0x1f94,0x3c198018,0x37398000)
    struct.pack_into('<I',exe,prefix+0x2bc80,msf_word(RESERVE_LBA))
    struct.pack_into('<I',exe,prefix+0x2bc84,msf_word(RESERVE_LBA+overlay_sectors))
    assert struct.unpack_from('<I',exe,prefix+0x2bcd0)[0] in (msf_word(RESERVE_LBA+256),msf_word(RESERVE_LBA+1024))
    struct.pack_into('<I',exe,prefix+0x2bcd0,msf_word(RESERVE_LBA+1024))
    changes=dict(changes);changes['SLPM_861.98']=bytes(exe)
    on_disc=dict(changes);on_disc['HAR/MENUMENU.BIN']=packed+bytes(menu_sectors_bytes-len(packed))+jobs
    report=dict(format='LZ4 block with size header; native R3000 decoder',decoded_bytes=MENU_READ_SIZE,
        compressed_bytes=len(packed),read_bytes=read_bytes,previous_read_bytes=0x68000,
        staging_address='0x801a0000',staging_end=hex(0x801a0000+read_bytes),
        output_address='0x80140000',output_end='0x801a0000',
        omitted_write_only_packet_pool_bytes=0x8000,
        overlay_lba=RESERVE_LBA,menu_lba=RESERVE_LBA+overlay_sectors,
        adjacent_extents=True,lossless_roundtrip=True,menu_relocations=routes,
        combined_read_bytes=combined_bytes,combined_staging_address='0x80188000',
        combined_staging_end=hex(0x80188000+combined_bytes),normal_entry_cd_reads=1,
        decoder_address='0x80037680',decoder_bytes=(ROOT/'work/menu-lz4.bin').stat().st_size,
        hooked_read_callers=['0x8003a1fc','0x80108eac','0x8010f988'])
    report.update(job_sprites_cached=True,job_sprite_bytes=len(jobs),job_sprite_cache_address=hex(job_source),
                  job_sprite_original_read='0x80110c7c',job_sprite_lz4_offset=menu_sectors_bytes)
    from field_menu_loading import prepare as prepare_field_return
    changes,field_report,field_banks=prepare_field_return(changes,RESERVE_LBA+overlay_sectors,RESERVE_LBA+544)
    on_disc['SLPM_861.98']=changes['SLPM_861.98']
    offset=field_report['bank_offset'];payload=on_disc['HAR/MENUMENU.BIN']
    assert len(payload)<=offset
    on_disc['HAR/MENUMENU.BIN']=payload+bytes(offset-len(payload))+field_banks
    assert overlay_sectors+(len(on_disc['HAR/MENUMENU.BIN'])+2047)//2048<=544
    (ROOT/'work/menu-disc.pac').write_bytes(on_disc['HAR/MENUMENU.BIN'])
    report['field_return']=field_report
    report['decoder_bytes']=field_report['resident_loader_bytes']
    report['bonus_relocation_lba']=RESERVE_LBA+1024
    bonus_path=ROOT/'analysis/omake-insertion.json'
    bonus=json.loads(bonus_path.read_text('utf8'))
    bonus['relocation_lba']=RESERVE_LBA+1024
    bonus['relocation_msf']=struct.pack('<I',msf_word(RESERVE_LBA+1024)).hex()
    bonus_path.write_text(json.dumps(bonus,ensure_ascii=False,indent=2)+'\n','utf8')
    (ROOT/'analysis/menu-loading.json').write_text(json.dumps(report,indent=2)+'\n','utf8')
    path=ROOT/'analysis/small-runtime.json'
    runtime=json.loads(path.read_text('utf8'))
    runtime.update(menu_read_bytes=read_bytes,menu_decoded_bytes=MENU_READ_SIZE,
        menu_loading_report='analysis/menu-loading.json')
    path.write_text(json.dumps(runtime,ensure_ascii=False,indent=2)+'\n','utf8')
    return changes,on_disc,routes
