"""Link bonus-menu half-width kana runs to reviewed Korean catalog names."""
import json,re,struct
from textcodec import ROOT
from korean_codec import CONTROL,normalize,JP
from translate_dialogue import GLOSSARY

def key(text):
    return ''.join(chr(ord(c)+96) if '\u3041'<=c<='\u3096' else c for c in normalize(text).replace('□','').replace('-','ー')).strip()

ALIASES={
'ナンバー':'넘버','ショクシュ':'촉수','キュアロータ':'큐어로터','ディッグアーマ':'디그아머','ビッグベア':'빅베어','ミキリノジュス':'회피의 염주',
'ウィークメーカー':'위크메이커','クリスタルオーブ':'크리스털 오브','ナッツンスーツ':'나쯘슈트','ナシ':'없음',
'ゾーナ・シーカー':'조나시커','ケット・シー':'케트시','アップボーナス':'상승 보너스','ジバク':'자폭',
'オモナシヨウモンスター':'사용 몬스터','ソノホカノモンスター':'기타 몬스터','ホカノモノ':'기타',
'アクセサリー':'장신구','ボウグ':'방어구','ブキ':'무기','カケタモノ':'건 물건','タイセンアイテ':'대전 상대','テニイレルモノ':'획득 물건',
'ムゲントウブ':'몽환투무','ユキダルマロンド':'눈사람 론도','ヤミノレクイエム':'어둠의 레퀴엠','ミズノハーモニー':'물의 하모니',
'ダイチノブルース':'대지의 블루스','アイノセレナーデ':'사랑의 세레나데','サバクノララバイ':'사막의 자장가','モリノノクターン':'숲의 야상곡','カゼノラプソディ':'바람의 랩소디',
'ユウレイ':'유령','テイコクヘイシ':'제국병','スーパーティナ':'슈퍼 티나','カッパ':'임프','シンカン':'신관','ショウグン':'장군','モノマネシ':'흉내쟁이','ヤセイジ':'야생아',
'ギャンブラー':'도박사','ピクトマンサー':'그림술사','アオマドウシ':'청마도사','ルーンナイト':'룬 나이트','モンク':'몽크','マシーナリー':'기공사',
'アサシン':'암살자','ボウケンカ':'트레저 헌터','マドウセンシ':'마도 전사','オボエタマホウ':'습득 마법','オドリ':'춤','ワースト':'최저',
'ダメージ':'피해량','レベル':'레벨','ホスウ':'걸음 수','ギル':'길','サイコウ':'최고','サイテイ':'최저','チカラ':'힘','スバヤサ':'민첩','タイリョク':'체력','マリョク':'마력','トクシュ':'특수'}

def main():
    fixed=json.loads((ROOT/'analysis/fixed-catalog-original.json').read_text('utf8'));ko=json.loads((ROOT/'translations/fixed-catalog.ko.json').read_text('utf8'))
    glossary={key(CONTROL.sub('',r['source'])):CONTROL.sub('',ko[str(r['id'])]['translation']).strip() for r in fixed}
    glossary.update({key(k):v for k,v in GLOSSARY.items()});glossary.update({key(k):v for k,v in ALIASES.items()})
    source=json.loads((ROOT/'analysis/omake-small-original.json').read_text('utf8'));strings=[];ids={};records=[];errors=[]
    for row in source:
        raw=bytes.fromhex(row['raw_hex'])
        # Internal kana/hiragana bank switches are typography, so combine the
        # whole Japanese word before catalog lookup. Keep an initial selector
        # at its original address for callers that skip those two bytes.
        prefix=raw[:2] if raw.startswith((b'%k',b'%K')) else b''
        raw=prefix+re.sub(rb'%[kK]',b'',raw[len(prefix):])
        patched=bytearray();cursor=0;refs=[]
        # The original font represents all of these labels with half-width kana.
        for match in re.finditer(rb'[\xa1-\xdf]+(?:-[\xa1-\xdf]+)*-?|%[HRDU](?:%[HRDU])*',raw):
            chunk=normalize(match[0].decode('cp932'));normalized=key(chunk)
            if match[0].startswith(b'%'):
                text=''.join({'H':'좌','R':'우','D':'하','U':'상'}[chr(c)] for c in match[0][1::2])
            else:
                if normalized not in glossary:errors.append({'id':row['id'],'source':chunk});continue
                text=normalize(glossary[normalized])
            if JP.search(text):raise ValueError('Japanese residual in linked catalog')
            if text not in ids:ids[text]=len(strings);strings.append(text)
            identifier=ids[text]
            if identifier>=1024:raise ValueError('Bonus small-reference capacity')
            patched+=raw[cursor:match.start()]+bytes((1+(identifier>>7),0x80+(identifier&127)));cursor=match.end();refs.append(identifier)
        patched+=raw[cursor:]+b'\0'
        if len(patched)>row['length']:raise ValueError(('Bonus reference exceeds literal',row['id'],len(patched),row['length']))
        records.append(dict(row,patched_hex=patched.hex(),reference_ids=refs))
    if errors:
        print(errors);raise ValueError('Unlinked bonus names')
    (ROOT/'translations/omake-small.ko.json').write_text(json.dumps({'strings':strings,'records':records},ensure_ascii=False,indent=2)+'\n','utf8')
    print('Linked',len(records),'small labels to',len(strings),'reviewed Korean strings.')
if __name__=='__main__':main()
