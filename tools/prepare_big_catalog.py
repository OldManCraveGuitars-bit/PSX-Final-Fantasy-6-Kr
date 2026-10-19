"""Reviewed esper, attack and summon terminology, shared across duplicate tables."""
import json
from textcodec import ROOT
from korean_codec import normalize,CONTROL

ESPERS='라무|이프리트|시바|세이렌|미드가르드오름|카토블레파스|마딘|비스마르크|케트시|케찰리|발리가르만다|오딘|라이딘|바하무트|알렉산더|지하드|라그나로크|기린|조나시커|카벙클|팬텀|세라핌|골렘|유니콘|펜리르|락슈미|피닉스'.split('|')
ATTACKS=(
 '화둔|수둔|뇌신|눈보라|조커 데스||||||||폭렬권|오라 캐논|메테오스트라이크|봉황의 춤|차크라|진공파|스파이럴 소울|몽환투무|'
 '칼바람|일광욕|나뭇잎 난무|삼림욕|모래바람|개미지옥|도깨비불|망령|절벽 붕괴|소닉 붐|엘니뇨|플라스마|함정|낙반|눈덩이|눈사태|'
 '코카트리스|웜뱃|미어캣|맥|멧돼지 새끼|너구리|독개구리|눈토끼|바이오블라스트|선 빔|초코보 러시|다이빙 봄|세븐 플래시|메가 쇼크|'
 '파이어 빔|선더 빔|블리자 빔|바이오블래스터|힐 포스|컨퓨저|데조네이터|마도 미사일|죽음의 선고|죽음의 룰렛|대해일|아쿠아브레스|에어로가|바늘천개|'
 '마이티 가드|리벤지블라스트|화이트 윈드|레벨 5 데스|레벨 4 플레어|레벨 3 컨퓨|리플레크????|레벨? 홀리|걸음 수 피해|포스 필드|괴음파|썩은 입김|융합|파문|돌팔매|퀘이사|그랜드 트라인|자폭|'
 '카파 송|투명화|독안개|가스트 스모크|섬광탄|자장가|산성비|혼란|메가 버서크|침묵|그물|끈적한 점액|델타 어택|휘감기|블래스터|대선풍|파이어볼|아토믹 레이|마도 레이저|확산 레이저|파동포|1만 볼트|100만 볼트|블리자드|절대영도|매그니튜드 8|흡수|플래시 레인|마도 배리어|마음없는 천사|배리어 체인지|도주|중력 50|마인드블라스트|노던 크로스|플레어 스타|사랑의 선고|포획|자기장 변환|타기팅|콧바람|서던 크로스|런처|유혹|프리징 더스트|문어발|하이퍼드라이브|트라인|마계의 기적|그래비티 봄|빨아들이기|디재스터|메탈 커터|봄 베어러|소화액|퓨리|내던지기|클라우디 헤븐|미사일|미싱|메테오|리벤저|폴터가이스트|공포의 시선|충격파|화염|소울 아웃|열풍살|샴시르|헤일스톤|세인트 빔|훔바바브레스|라이프 셰이버|파이어 월|랜드슬라이드|공격|특수|라이엇 소드|미라주 다이브|제비반환|섀도 팽|로열 쇼크|타이거 브레이크|스피닝 에지|세이버 소울|스타 프리즘|블러디 카드|모그리 난무|응징의 메테오|하운드 태클|와일드 팽|미시디아 토끼|미사용'
).split('|')
SUMMONS='심판의 번개|지옥의 화염|다이아몬드더스트|루나틱 보이스|어스 서라운드|악마의 눈동자|카오스 웨이브|버블 블로|캣 레인|소닉 다이브|트라이디재스터|참철검|진·참철검|메가플레어|성스러운 심판|천지붕괴|메타모르포스|홀리 브라이튼|매직 실드|루비의 빛|배니싱 보디|엔젤 페더|어스 월|힐 혼|하울링 문|매혹의 포옹|전생의 불꽃'.split('|')

def main():
    original=json.loads((ROOT/'analysis/fixed-catalog-original.json').read_text('utf8'))
    path=ROOT/'translations/fixed-catalog.ko.json';rows=json.loads(path.read_text('utf8'))
    assert (len(ESPERS),len(ATTACKS),len(SUMMONS))==(27,175,27),(len(ESPERS),len(ATTACKS),len(SUMMONS))
    for row in original:
        choices={'esper':ESPERS,'attack':ATTACKS,'esper_attack':SUMMONS}.get(row['category'])
        if choices is not None:rows[str(row['id'])].update(translation=choices[row['index']],status='manual_context_checked')
    terms={normalize(CONTROL.sub('',r['source'])).strip():CONTROL.sub('',rows[str(r['id'])]['translation']).strip()
        for r in original if rows[str(r['id'])].get('status')=='manual_context_checked' and CONTROL.sub('',r['source']).strip()}
    reused=0
    for row in original:
        source=normalize(CONTROL.sub('',row['source'])).strip()
        if row['category']=='monster_attack' and source in terms:
            rows[str(row['id'])].update(translation=terms[source],status='manual_context_checked');reused+=1
    path.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n','utf8')
    print('Reviewed 229 large-name entries; reused',reused,'matching monster abilities')
if __name__=='__main__':main()
