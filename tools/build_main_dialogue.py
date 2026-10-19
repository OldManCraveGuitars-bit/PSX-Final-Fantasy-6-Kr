"""Build an explicitly incomplete native-dialogue development candidate."""
import json,struct,re
from textcodec import ROOT
from korean_codec import *
from dte import compress_text,patch_table,choose_dictionary
from pac import compress,decompress
from cdimage import build_image
from textlayout import wrap,center_prologue
from small_ui import patch as patch_small_ui
from small_runtime import patch as patch_small_runtime
from field_names import default_names,patch as patch_field_names
from psx_ui import patch as patch_psx_ui
from battle_runtime import patch as patch_battle_runtime
from movie_subtitles import patch as patch_movie_subtitles
from omake_runtime import patch as patch_omake
from gallery_text import patch as patch_gallery
from dialogue_runtime import pack as pack_dialogue,insert_runtime as insert_dialogue_runtime

BASE=0x800c8000
CANDIDATE='FF6-KR-main-development-v080'
SPECIAL=[(0x5b83,0),(0x55a0,1),(0x86ba,2),(0x580a,3),(0x56c2,4),(0x56da,5),(0x572d,6),(0x5c97,7),(0x81e,8),(0x7f8a,9),(0x17238,10),(0x1a343,11),(0xbea5,12),(0xbf58,13),(0x12788,14),(0xf360,15)]

def jump(address):return (2<<26)|((address>>2)&0x3ffffff)
def load(reg,value):
    if value<=0xffff:return [(13<<26)|(reg<<16)|value]
    return [(15<<26)|(reg<<16)|(value>>16),(13<<26)|(reg<<21)|(reg<<16)|(value&65535)]

def expand(data,dictionary):
    out=bytearray();p=0
    while p<len(data):
        c=data[p];p+=1
        if 0xd9<=c<=0xef:out+=dictionary[c-0xd9][1]
        else:
            out.append(c)
            if c in (0x11,0x14,0x16,0x1c,0x1d,0x1e,0x1f):out+=data[p:p+1];p+=1
    return out

def main():
    from prepare_translation import main as consolidate_dialogue
    # Canonical prose is reviewed/imported in the standalone text manager.
    # Building must never silently rewrite its punctuation or wording.
    consolidate_dialogue()
    rows=json.loads((ROOT/'translations/dialogue.complete-draft.json').read_text('utf-8'))
    aux=json.loads((ROOT/'translations/psx_auxiliary.json').read_text('utf-8'))
    titles=json.loads((ROOT/'translations/map-titles.json').read_text('utf-8'))
    # Use verified hexadecimal addresses; JSON keeps the matching readable records.
    addresses=[0x801c5580,0x801c569c,0x801c56cc,0x801c5728,0x801c5778,0x801c57a0,0x801c5800,0x801c5840,0x801c58a0,0x801c5914,0x801c597c,0x801c59b0,0x801c59e4,0x801c5a6c,0x801c5ae8,0x801c5b28]
    for x,a in zip(aux,addresses):x['original_address']=a
    texts=[x['translation'] for x in rows+aux+titles]+default_names()
    reserved_field_glyphs=set(range(184,223))|set(range(51,64))|set(range(1085,1100))
    mapping,assigned=allocate(texts,reserved_indices=reserved_field_glyphs);save_allocation(mapping,assigned)
    widths=bytearray((ROOT/'work/extracted/NAR/NAR_BIN.BIN').read_bytes()[0x646d0:0x64bd0])
    for _,old,new in fixed_relocations(mapping,assigned):widths[font_index(new)+32]=widths[font_index(old)+32]
    wrapped_count=0
    for row in rows+aux:
        wrapped=wrap(row['translation'],mapping,assigned,widths)
        if row in rows and row['id'] in (6,7,8,9):wrapped=center_prologue(wrapped,mapping,assigned,widths)
        wrapped_count+=wrapped!=row['translation'];row['translation']=wrapped
    (ROOT/'analysis/dialogue-native-layout.json').write_text(json.dumps(rows+aux,ensure_ascii=False,indent=2)+'\n','utf8')
    dictionary=choose_dictionary([x['translation'] for x in rows+aux],mapping)
    plan={'dictionary':[{'code':hex(0xd9+i),'text':t,'bytes':b.hex()} for i,(t,b) in enumerate(dictionary)],
        'mte_table_bytes':sum((len(b)+4)&~3 for _,b in dictionary),'source':'current wrapped Korean dialogue'}
    (ROOT/'analysis/korean-mte-plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n','utf8')
    nar=bytearray((ROOT/'work/extracted/NAR/NAR_BIN.BIN').read_bytes())
    script=bytearray((ROOT/'work/extracted/NAR/NAR_BIN3.BIN').read_bytes())
    pac=bytearray((ROOT/'work/decompressed/NAR/NARITA.PAC').read_bytes())
    streams=[]
    for row in rows+aux:
        data=compress_text(row['translation'],mapping,dictionary)
        assert expand(data,dictionary)==encode(row['translation'],mapping)
        streams.append(data+b'\0')
    packed,new_offsets,aux_offsets,main_size,huffman,dialogue_report=pack_dialogue(streams,len(rows))
    map_data=bytearray()
    for i,item in enumerate(titles):
        struct.pack_into('<H',script,0x1b000+i*2,len(map_data))
        map_data+=encode(item['translation'],mapping)+b'\0'
    if len(map_data)>0x250:raise ValueError('Map-title allocation overflow')
    script[0x1b0c0:0x1b310]=map_data+bytes(0x250-len(map_data))
    if len(packed)>0x1afa0:raise ValueError(f'Dialogue allocation overflow {len(packed)}>110496')
    script[:0x1afa0]=packed+bytes(0x1afa0-len(packed))
    script_used,dialogue_symbols=insert_dialogue_runtime(script,len(packed),huffman,dialogue_report)
    # A record can land exactly on 64 KiB without the padding branch firing.
    bank_index=next((i for i,offset in enumerate(new_offsets) if offset>=65536),len(rows))
    struct.pack_into('<H',nar,0x6b710,bank_index)
    for i,offset in enumerate(new_offsets):struct.pack_into('<H',nar,0x6b712+i*2,offset&65535)
    nar[0x64bd0:0x6b710]=build_large(nar[0x64bd0:0x6b710],assigned,mapping)
    pac=patch_table(pac,dictionary)
    # The live dialogue renderer indexes the 1280-byte width table with the
    # decoded character number (including the 32 control slots).
    for code in assigned.values():
        index=font_index(code)+32
        nar[0x646d0+index]=12
        pac[0x56260+index]=12
    for _,old,new in fixed_relocations(mapping,assigned):
        index=font_index(new)+32
        nar[0x646d0+index]=widths[font_index(old)+32]
        pac[0x56260+index]=widths[font_index(old)+32]
    # U+0020 is FF, which advances half the ordinary 12-pixel character cell.
    nar[0x646d0+0xff]=6
    pac[0x56260+0xff]=6
    nar,pac=patch_field_names(nar,pac,mapping,assigned)
    # Replace the PSX-specific dispatch with new offsets, preserving each alternate tutorial.
    if pac[0x80101ea8-BASE:0x80101eb0-BASE]!=bytes.fromhex('975c02345c000212'):raise ValueError('Dispatch hook guard failed')
    hook=0x80101ea8
    # The area after the original overlay belongs to BSS. Keep its dispatch
    # inside the original function; the decoder lives in the script resource.
    # Preserve incoming scratch state too: the original compiled routine leaves
    # these values intact at this point. The o32 outgoing argument area is free.
    instructions=[(43<<26)|(29<<21)|(r<<16)|o for r,o in [(4,0),(5,4),(3,8)]]
    instructions+=[(16<<21)|(3<<11)|0x21]+load(4,0x801b0000)+load(5,0x801c0000)
    branch_fixups=[]
    old_to_new={x['offset']:new_offsets[i] for i,x in enumerate(rows)}
    for old,index in SPECIAL:
        if old not in old_to_new:raise ValueError(f'Unmapped special offset {old:x}')
        instructions+=load(2,old_to_new[old])
        branch_fixups.append(len(instructions))
        instructions.append((4<<26)|(3<<21)|(2<<16))
        target=0x801a6200+aux_offsets[index];reg=4 if target>>16==0x801b else 5
        if target>>16 not in (0x801b,0x801c):raise ValueError('Auxiliary base out of dispatch range')
        instructions.append((13<<26)|(reg<<21)|(16<<16)|(target&65535))
    instructions+=[(3<<21)|(16<<11)|0x21]+load(2,0x801a6200)+[(16<<21)|(2<<16)|(16<<11)|0x21]
    restore_at=hook+len(instructions)*4
    for i in branch_fixups:instructions[i]|=((restore_at-(hook+i*4)-4)//4)&65535
    instructions += [(35<<26)|(29<<21)|(r<<16)|o for r,o in [(4,0),(5,4),(3,8)]]
    instructions += [jump(dialogue_symbols['kr_dialogue_dispatch']),0]
    code=struct.pack('<'+'I'*len(instructions),*instructions)
    capacity=0x80101fcc-hook
    if len(code)>capacity:raise ValueError(f'Dispatch size overflow {len(code)}>{capacity}')
    pac[hook-BASE:0x80101fcc-BASE]=code+bytes(capacity-len(code))
    from field_catalog import patch as patch_field_catalog
    nar,script,pac=patch_field_catalog(nar,script,pac,mapping,script_used)
    compressed=compress(bytes(pac));assert decompress(compressed)[0]==pac
    original_pac=(ROOT/'work/extracted/NAR/NARITA.PAC').read_bytes()
    if len(compressed)>len(original_pac):raise ValueError(f'PAC allocation overflow {len(compressed)}>{len(original_pac)}')
    compressed+=bytes(len(original_pac)-len(compressed))
    changes={'NAR/NAR_BIN.BIN':bytes(nar),'NAR/NAR_BIN3.BIN':bytes(script),'NAR/NARITA.PAC':compressed}
    # Menu boost code uses a fixed resident entry address, compiled first.
    from movie_subtitles import prepare as prepare_resident
    prepare_resident()
    changes.update(patch_small_runtime(patch_small_ui()))
    changes=patch_psx_ui(changes)
    changes=patch_battle_runtime(changes)
    changes=patch_movie_subtitles(changes)
    changes=patch_omake(changes)
    changes=patch_gallery(changes)
    from boost_settings import patch as patch_boost
    changes=patch_boost(changes)
    from menu_loading import prepare as prepare_menu_disc
    changes,disc_changes,menu_routes=prepare_menu_disc(changes)
    name=CANDIDATE
    target,report=build_image(ROOT,disc_changes,name,relocations={**menu_routes,'OMAKEDIR/OMAKE.PAC':{'reserve':'DUMMY0.DAT','sector_offset':1024},'BTL/FF6_BTL.BIN':'DUMMY1.DAT','SLPM_861.98':'DUMMY2.DAT'},resizes={'DEODIR/DEO.PAC':0x13000,'BTL/BATTLE.PAC':0x4c000})
    report['menu_loading']=json.loads((ROOT/'analysis/menu-loading.json').read_text('utf8'))
    report.update(dialogue_count=len(rows),auxiliary_count=len(aux),wrapped_dialogue_count=wrapped_count,layout_limit_pixels=216,map_title_count=len(titles),map_title_bytes=len(map_data),main_bytes=main_size,all_script_bytes=len(packed),glyph_count=len(assigned),small_menu_headings=7,bank_index=bank_index,mte_dictionary_entries=len(dictionary),hook_address=hex(hook),bss_preserved=True,dispatch_bytes=len(code),space_widths={'large':6,'small':4},prologue_alignment='center',name_entry_native=False,incomplete=['field catalog and PSX extra/credit text paths','memory-card preview names','opera lyric identification and timed subtitle cues','runtime verification of expanded battle paths','review remaining machine-translated dialogue and descriptions'])
    report.update(name_entry_native='native composition, field/menu display, two-file physical save/load and independent per-file preview fonts verified',name_limit=6,default_name_count=64)
    report.update(positioned_menu_labels=265,menu_catalog_entries=775,menu_job_titles=64,menu_large_name_entries=606,menu_descriptions=377,
        field_catalog_names=310,battle_catalog_names=790,battle_large_text_records=1758,battle_native_name_paths='command, spell, item, monster, character, esper and attack; expanded native gameplay verification pending',movie_subtitle_cell=[12,12],movie_subtitle_encoding='separate native renderer; original STR files preserved',movie_subtitle_cues=json.loads((ROOT/'analysis/movie-subtitles-runtime.json').read_text('utf8'))['cue_count'])
    report.update(psx_save_load_messages=74,psx_small_ui_labels=json.loads((ROOT/'analysis/psx-ui-insertion.json').read_text('utf8'))['small_label_records'],psx_preview_job_labels=18,psx_window_tile_grid_pixels=8)
    report.update(dialogue_compression='MTE + lossless canonical Huffman per record',
        dialogue_raw_bytes=dialogue_report['raw_bytes'],dialogue_runtime_bytes=dialogue_report['runtime_bytes'],
        dialogue_expansion_buffer=hex(dialogue_report['buffer_address']))
    report.update(bonus_menu_large_records=578,bonus_menu_small_literals=len(json.loads((ROOT/'translations/omake-small.ko.json').read_text('utf8'))['records']),bonus_menu_native_gameplay='pending')
    battle_rows=json.loads((ROOT/'translations/battle-abilities.ko.json').read_text('utf8'))
    battle_pending=sum(bool(x['source'].strip()) and not x.get('status','').startswith('manual') for x in battle_rows.values())
    review_pending=any(x.get('status')=='machine_draft' for x in rows) or battle_pending
    report.update(incomplete=['unextracted static text and credit assets',
        'opera lyric identification and timed subtitle cues','expanded battle dialogue caller/timing gameplay verification']+(['review remaining machine-translated dialogue and monster cries'] if review_pending else []),
        menu_ui_fix='native job-title references and per-letter texture routing; original canvas texture pages retained',
        large_font='original size retained: menu Galmuri9 12x11 bitmap / 12-pixel advance; bonus Galmuri9 12x12')
    report.update(manually_reviewed_dialogue=sum(x.get('status')=='manual' for x in rows),
        machine_draft_dialogue=sum(x.get('status')=='machine_draft' for x in rows),
        reviewed_battle_ability_records=sum(x.get('status','').startswith('manual') for x in battle_rows.values()),
        machine_draft_battle_dialogue=battle_pending)
    gallery=json.loads((ROOT/'analysis/gallery-text-insertion.json').read_text('utf8'))
    report.update(gallery_text_records=gallery['records'],gallery_text_pages=gallery['pages'],gallery_artwork_preserved='palette, headers, padding and pixels outside reviewed text regions byte-identical')
    report['boost']=json.loads((ROOT/'analysis/boost-runtime.json').read_text('utf8'))
    report['boost_ON_explanations_displayed']=False
    report['magic_order_labels']=['회복','공격','보조']
    report['proofreading_report']='analysis/proofreading-v072-verification.json'
    out=target.parent;(out/'build-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf-8')
    (out/'omake-insertion.json').write_bytes((ROOT/'analysis/omake-insertion.json').read_bytes())
    (out/'omake-runtime.bin').write_bytes((ROOT/'work/omake-runtime.bin').read_bytes())
    (out/'new_dialogue_offsets.json').write_text(json.dumps(new_offsets),'utf-8')
    (ROOT/'work/modified').mkdir(exist_ok=True)
    for path,data in changes.items():
        file=ROOT/'work/modified'/path;file.parent.mkdir(parents=True,exist_ok=True);file.write_bytes(data)
    print(json.dumps({k:v for k,v in report.items() if k!='changed_lbas'},ensure_ascii=False))
if __name__=='__main__':main()
