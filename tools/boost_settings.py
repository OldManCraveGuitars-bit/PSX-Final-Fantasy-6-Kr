"""Build native configuration strings and guarded gameplay hook routing."""
import json,struct
from textcodec import ROOT
from boost_format import validate_boost_rows
from small_text import ascii_glyphs
from pac import compress,decompress

def texts():
    rows=json.loads((ROOT/'translations/boost-options.ko.json').read_text('utf8'))
    validate_boost_rows(rows)
    return rows

def prepare_menu(mapping):
    rows=texts();ascii_table=ascii_glyphs()
    symbols=json.loads((ROOT/'analysis/movie-subtitles-runtime.json').read_text('utf8'))['symbols']
    lines=[f'#define KR_BOOST_FLAGS_ADDRESS 0x{symbols["kr_boost_flags"]:08x}U']
    for key,row in rows.items():
        data=[]
        for c in row['translation']:
            tile=0x8ffe if c==' ' else mapping[c] if c in mapping else ascii_table[ord(c)]
            if tile==255:raise ValueError(('Missing native boost glyph',key,c))
            data.append(tile)
        data.append(0xffff)
        lines.append(f'static const unsigned short kr_boost_text_{key}[] DATA={{'+','.join(map(str,data))+'};')
    (ROOT/'work/boost-text-data.h').write_text('\n'.join(lines)+'\n','ascii')

def patch(changes):
    report=json.loads((ROOT/'analysis/movie-subtitles-runtime.json').read_text('utf8'))
    symbols=report['symbols'];changes=dict(changes);hooks=[]
    for file,address,symbol,guard,link in [
        ('NAR/NARITA.PAC',0x800d238c,'kr_boost_field_check','d249030c00000000',True),
        ('BTL/BATTLE.PAC',0x80169404,'kr_boost_rewards','212020020280053c',True),
        ('OGA/OGATA.PAC',0x800cdf44,'kr_boost_world_check','0780023c6cc1428c',False),
    ]:
        if file in changes:data=decompress(changes[file])[0]
        else:data=(ROOT/'work/decompressed'/file).read_bytes()
        data=bytearray(data);at=address-0x800c8000
        if data[at:at+8].hex()!=guard:raise ValueError(('Boost hook guard',file,hex(address),data[at:at+8].hex()))
        struct.pack_into('<II',data,at,((3 if link else 2)<<26)|((symbols[symbol]>>2)&0x3ffffff),0)
        packed=compress(bytes(data));source=(ROOT/'work/extracted'/file).read_bytes()
        capacity=(len(source)+2047)//2048*2048
        if len(packed)>capacity:raise ValueError(('Boost overlay capacity',file,len(packed),capacity))
        changes[file]=packed+bytes(max(0,len(source)-len(packed)))
        hooks.append(dict(file=file,address=hex(address),symbol=symbol,guard=guard))
    result=dict(default_flags=0,options=['disable_random_encounters','experience_x5','gil_x5','AP_x5'],
        input='Configuration -> SELECT: boost page; up/down select; left OFF/right ON; confirm toggles; cancel/SELECT returns.',
        storage='KRN1 reserved header bytes 8..15, BST1 tag and checked four-bit value; both live and save mirror; native save size unchanged.',
        new_game_reset=True,rewards='Native defeated-monster totals before XP division, learning, relic effects, messages and original caps.',
        overflow='24-bit reward saturation; AP saturated at native 255.',
        hooks=hooks,resident_symbols={k:v for k,v in symbols.items() if k.startswith('kr_boost')},
        native_verification_reports=['analysis/boost-native-menu-verification.json',
            'analysis/boost-native-rewards-verification.json',
            'analysis/boost-native-save-load-verification.json'])
    (ROOT/'analysis/boost-runtime.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n','utf8')
    return changes
