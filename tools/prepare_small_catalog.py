"""Context-checked command/spell terminology before insertion."""
import json,re
from textcodec import ROOT

COMMANDS=['공격','도구','마법','트랜스','돌아가기','훔치기','강탈','필살검','던지기','기계','필살기','마봉검','청마법','스케치','조종','슬롯','날뛰기','뛰어들기','흉내','춤','대열','방어','점프','연속마법','돈 던지기','소환','기도','쇼크','빙의','마도','','']
SPELLS=['파이어','블리자드','선더','포이즌','드레인','파이라','블리자라','선더라','바이오','파이가','블리자가','선더가','브레이크','데스','홀리','플레어','그라비데','그라비가','데존','메테오','알테마','퀘이크','토네이도','멜튼','라이브라','슬로우','라스필','사일레스','프로테스','슬리플','콘퓨','헤이스트','스톱','버서크','레비테트','카파','리플렉','셸','배니시','헤이스가','슬로우가','아스필','텔레포','퀵','디스펠','케알','케알라','케알가','레이즈','어레이즈','포이조나','에스나','리제네','리레이즈']

def main():
    original=json.loads((ROOT/'analysis/fixed-catalog-original.json').read_text('utf8'))
    path=ROOT/'translations/fixed-catalog.ko.json';draft=json.loads(path.read_text('utf8'))
    count=0
    for row in original:
        if row['category']=='command':text=COMMANDS[row['index']]
        elif row['category']=='spell':
            icon=re.match(r'\{[^{}]+\}',row['source'])
            text=(icon[0] if icon else '')+SPELLS[row['index']]
        else:continue
        draft[str(row['id'])]['translation']=text;draft[str(row['id'])]['status']='manual_context_checked';count+=1
    path.write_text(json.dumps(draft,ensure_ascii=False,indent=2)+'\n','utf8')
    print('Command/spell names checked:',count)

if __name__=='__main__':main()
