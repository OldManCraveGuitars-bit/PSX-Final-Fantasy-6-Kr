"""Context-reviewed descriptions for Blitz, Bushido and Lore."""
import json
from textcodec import ROOT

TEXTS=[
 '적 하나에게 방어 무시 피해','적 하나에게 성스러운 기로 피해','적 하나를 내던지는 기술',
 '적들에게 불 속성 피해','자신을 제외한 아군을 회복','적들에게 바람 속성 피해',
 '목숨을 바쳐 동료를 회복','적 하나에게 큰 피해',
 '적 하나에게 피해','적 하나에게 반격으로 큰 피해','적 하나의 HP를 절반으로 감소',
 '적을 네 번 공격','적 하나에게서 HP와 MP 흡수','적들에게 피해와 스톱',
 '적을 네 번 공격','적들을 일도양단',
 '카운트다운 뒤 데스','룰렛으로 대상을 정하는 데스','물 속성 피해','바람·물 속성 피해',
 '바람 속성 피해','1000 피해','아군 전체에 셸과 프로테스','자신이 잃은 HP만큼 피해',
 '자신의 HP만큼 아군을 회복','레벨이 5의 배수인 적에게 데스','레벨이 4의 배수인 적에게 플레어',
 '레벨이 3의 배수인 적에게 혼란','리플렉 상태의 적에게 상태 공격','레벨이 ?인 적에게 홀리',
 '걸음 수에 따른 피해','공간에 속성을 무효화하는 장벽 설치','적의 레벨을 절반으로 감소',
 '적에게 상태 공격','목숨을 동료에게 맡김','적과 상태를 교환','피해와 혼란',
 '적 전체에 방어 무시 피해','적 전체에 방어를 무시하는 큰 피해','목숨을 바쳐 큰 피해'
]
def main():
    path=ROOT/'translations/battle-abilities.ko.json';rows=json.loads(path.read_text('utf8'))
    assert len(TEXTS)==40
    for i,text in enumerate(TEXTS,256):rows[str(i)].update(translation=text,status='manual_context_checked')
    rows['33'].update(translation='크워어어!!{pause}',status='manual_context_checked')
    path.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n','utf8')
    print('Reviewed 40 ability descriptions and battle cry 33')
if __name__=='__main__':main()
