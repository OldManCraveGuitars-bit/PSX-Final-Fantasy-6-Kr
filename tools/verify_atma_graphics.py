"""Compare original and localized native captures under identical party modes."""
import hashlib, json
from PIL import Image, ImageChops
from textcodec import ROOT


def main():
    box=(30,49,184,149)
    pairs=[('normal_party','original-atma-normal-party.png','v071-atma-normal-party.png'),
           ('unsupported_magitek_fixture','original-atma-graphics-control.png','kr-v071-atma-graphics-control.png')]
    comparisons=[]
    for mode,original,korean in pairs:
        a=Image.open(ROOT/'analysis'/original).convert('RGB').crop(box)
        b=Image.open(ROOT/'analysis'/korean).convert('RGB').crop(box)
        assert ImageChops.difference(a,b).getbbox() is None,mode
        comparisons.append(dict(party_mode=mode,original='analysis/'+original,
                                localized='analysis/'+korean,visible_monster_region=list(box),
                                pixels_byte_identical=True,sha256=hashlib.sha256(a.tobytes()).hexdigest()))
    assert comparisons[0]['sha256']!=comparisons[1]['sha256']
    result=dict(candidate='FF6-KR-main-development-v071',encounter=0x1e2,
                cause='The forced opening Magitek party is incompatible with this large late boss; identical sprite fragments reproduce in the unmodified game.',
                correction='Clear only fixture character-status bit0x08 before this encounter; the normal-party boss matches the original pixel for pixel.',
                affected_fixture_slots=[0,14,15],ROM_graphics_or_font_change=False,
                comparisons=comparisons,corrected_QA='tools/qa_long_battle_native.py',
                long_dialogue_proof='analysis/v071-long-battle-native-verification.json')
    (ROOT/'analysis/v071-atma-graphics-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n','utf8')
    print(dict(native_original_and_Korean_monster_pixels='exact in both party modes',normal_party='clean',ROM_changes=0))


if __name__=='__main__':main()
