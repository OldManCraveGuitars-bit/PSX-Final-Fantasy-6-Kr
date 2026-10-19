"""Extract the 73 verified map-title pointers and pair human translations."""
import json,struct
from textcodec import ROOT,decode
from extract_descriptions import string_end

KOREAN=[
 '', '여관','무기점','방어구점','무기·방어구점','액세서리점','도구점','술집','기관실',
 '지하 1층','지하 2층','지하 3층','지하 4층','1층','2층','3층','4층','5층','6층','7층','8층','9층','10층',
 '초코보 대여점','피가로 성','사우스 피가로 마을','리터너 본부','장로의 집','무도가 던컨의 집','콜츠 산','왕의 방','모그리 동굴',
 '탄광 도시 나르셰','경매장','아우저의 저택','바렌 폭포','모블리즈 마을','항구 도시 니케아','첸 마을','리터너 본부','레테 강',
 '제국군 진지','도마 성','미혹의 숲','뱀의 길','코링겐 마을','조조','지돌 마을','오페라 극장','제국 수도 벡터','제국 성','마도 연구소',
 '마란다 마을','알브루크 마을','봉마벽 감시소','봉마벽','사마사 마을','용의 목 콜로세움','대릴의 무덤·지하 1층','마대륙','환수 마을',
 '조조 산','마도 공장','초승달 산','초보자의 집','케프카의 탑','조금 어려운 전투의 방','전투의 방','필드의 방','봉마벽으로 가는 동굴',
 '무기·방어구·도구점','피닉스 동굴','짐승의 평원 동굴'
]

def main():
    data=(ROOT/'work/extracted/NAR/NAR_BIN3.BIN').read_bytes()
    pointers=struct.unpack_from('<73H',data,0x1b000)
    assert len(KOREAN)==len(pointers)==73
    rows=[]
    for i,(offset,ko) in enumerate(zip(pointers,KOREAN)):
        start=0x1b0c0+offset;end=string_end(data,start)
        assert offset<0x250 and end<=0x1b310
        raw=data[start:end]
        rows.append({'id':i,'source':decode(raw,'dialog',stop=True),'translation':ko,'status':'manual','original_offset':offset,'original_hex':raw.hex()})
    (ROOT/'translations/map-titles.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n','utf8')
    print('Extracted and translated',len(rows),'map titles')

if __name__=='__main__':main()
