"""Resolve quoted Japanese technique/item names to the reviewed catalog."""
import json,re
from textcodec import ROOT
from korean_codec import CONTROL
from prepare_omake_small import key,ALIASES
from translate_dialogue import GLOSSARY

def glossary():
    src=json.loads((ROOT/'analysis/fixed-catalog-original.json').read_text('utf8'));ko=json.loads((ROOT/'translations/fixed-catalog.ko.json').read_text('utf8'))
    terms={key(CONTROL.sub('',r['source'])):CONTROL.sub('',ko[str(r['id'])]['translation']).strip() for r in src}
    terms.update({key(k):v for k,v in GLOSSARY.items()});terms.update({key(k):v for k,v in ALIASES.items()})
    terms.update({key(k):v for k,v in {'しぬまでみかたをなぐりなさい':'죽을 때까지 동료를 때려라','きほんプログラム':'기본 프로그램','せんとうプログラム':'전투 프로그램','レーザー':'레이저','しゃりん':'차륜','まどうバリア':'마도 배리어','クリティカル':'치명타','ショクシュ':'촉수','やみのレクイエム':'어둠의 레퀴엠','まどうアーマー':'마도 아머','どくけし':'해독제','めぐすり':'안약','げんじのこて':'겐지의 장갑'}.items()})
    return terms

def save_manual(updates):
    (ROOT/'work/omake-manual-pending.json').write_text(json.dumps(updates,ensure_ascii=False,indent=2)+'\n','utf8')
    terms=glossary()
    kana=str.maketrans('ァィゥェォャュョッヵヶ','アイウエオヤユヨツカケ')
    relaxed={k.translate(kana).replace(' ',''):v for k,v in terms.items()}
    terms[key('必殺剣 空')]='필살검 공'
    def term(m):
        source=m[1];k=key(source)
        if k in terms:return terms[k]
        alternate=k.translate(kana).replace(' ','')
        if alternate in relaxed:return relaxed[alternate]
        raise ValueError('Unlinked quoted term '+source)
    p=ROOT/'translations/omake-manual.json';manual=json.loads(p.read_text('utf8'))
    for i,text in updates.items():manual[str(i)]=re.sub(r'【([^】]+)】',term,text)
    p.write_text(json.dumps(manual,ensure_ascii=False,indent=2)+'\n','utf8')
    src=json.loads((ROOT/'analysis/omake-original.json').read_text('utf8'))
    output={str(r['id']):{'source':r['source'],'translation':manual[str(r['id'])],'status':'manual'} for r in src if str(r['id']) in manual}
    (ROOT/'translations/omake.ko.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n','utf8')
    print('Reviewed bonus rows',len(output),'/',len(src))
