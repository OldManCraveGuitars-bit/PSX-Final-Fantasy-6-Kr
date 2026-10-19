"""Stage the OPEN.STR text transcription; import canonical text with the EXE."""
import json
from textcodec import ROOT
from caption_format import pack_caption_text

# Original, unmodified OPEN.STR frames, 15 frames per second. Each interval
# follows the legible part of its fade, excluding the preceding/following card.
ROWS = [
    (472,604,'SQUARESOFT','스퀘어소프트'),
    (622,674,'PRODUCER\nHironobu Sakaguchi','제작\n사카구치 히로노부'),
    (711,741,'DIRECTOR\nYoshinori Kitase\nHiroyuki Itou','감독\n키타세 요시노리·이토 히로유키'),
    (742,771,'MAIN PROGRAMMER\nKen Narita\nKiyoshi Yoshii','메인 프로그래밍\n나리타 켄·요시이 기요시'),
    (772,795,'GRAPHIC DIRECTOR\nTetsuya Takahashi\nKazuko Shibuya','그래픽 감독\n다카하시 데쓰야·시부야 가즈코'),
    (796,821,'GRAPHIC DIRECTOR\nHideo Minaba\nTetsuya Nomura','그래픽 감독\n미나바 히데오·노무라 데쓰야'),
    (822,850,'MUSIC COMPOSER\nNobuo Uematsu','작곡\n우에마쓰 노부오'),
    (879,899,'IMAGE DESIGNER\nYoshitaka Amano','이미지 디자인\n아마노 요시타카'),
    (899,920,'BATTLE PLANNER\nYasuyuki Hasebe','전투 기획\n하세베 야스유키'),
    (921,946,'FIELD PLANNER\nSatoru Tsuji\nHidetoshi Kezuka','필드 기획\n쓰지 사토루·게즈카 히데토시'),
    (947,978,'EFFECT PROGRAMMER\nHiroshi Harata\nSatoshi Ogata','효과 프로그래밍\n하라타 히로시·오가타 사토시'),
    (979,1003,'EVENT PLANNER\nTsukasa Fujita\nKeisuke Matsuhara','이벤트 기획\n후지타 쓰카사·마쓰하라 게이스케'),
    (1004,1042,'BATTLE PROGRAMMER\nAkihiro Yamaguchi','전투 프로그래밍\n야마구치 아키히로'),
    (1168,1198,'SOUND PROGRAMMER\nMinoru Akao','음향 프로그래밍\n아카오 미노루'),
    (1199,1222,'EFFECT GRAPHIC DESIGNER\nHirokatsu Sasaki','효과 그래픽\n사사키 히로카쓰'),
    (1223,1249,'FIELD GRAPHIC DESIGNER\nTakaharu Matsuo\nYusuke Naora\nNobuyuki Ikeda','배경 그래픽\n마쓰오 다카하루·나오라 유스케·이케다 노부유키'),
    (1250,1283,'FIELD GRAPHIC DESIGNER\nTomoe Inazawa\nTakamich Shibuya','배경 그래픽\n이나자와 도모에·시부야 다카미치'),
    (1318,1354,'FIELD GRAPHIC DESIGNER\nShinichirou Hamasaka\nAkiyoshi Masuda','배경 그래픽\n하마사카 신이치로·마스다 아키요시'),
    (1355,1390,'MONSTER GRAPHIC DESIGNER\nHitoshi Sasaki','몬스터 그래픽\n사사키 히토시'),
    (1415,1440,'OBJECT GRAPHIC DESIGNER\nKazuhiro Ohkawa','오브젝트 그래픽\n오카와 가즈히로'),
    (1441,1462,'SOUND ENGINEER\nEiji Nakamura','음향 엔지니어\n나카무라 에이지'),
    (1590,1685,'Command to the Empire Force in particular.\n帝国軍特別指令','제국군 특별 지령'),
    (1698,1788,'Commence to launch the attack on Narche,\nthe coal mines city.\n炭坑都市「ナルシェ」への侵攻作戦開始','탄광 도시 나르셰의\n침공 작전을 개시하라.'),
    (2805,2868,'FINAL FANTASY VI\nファイナルファンタジーVI','파이널 판타지 VI'),
]

def main():
    rows=[dict(movie='OPEN',start_frame=a,end_frame=b,source=source,translation=text,
        evidence=f'Original MOVIE/OPEN.STR, 15 fps, decoded frames {a}..{b-1}',status='manual')
        for a,b,source,text in ROWS]
    data,mapping,font=pack_caption_text(rows)
    path=ROOT/'work/opening-caption-import.json'
    path.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n','utf8')
    print({'staging':str(path),'cues':len(rows),'glyphs':len(mapping)-2,'font_offset':font,'used_bytes':font+(len(mapping)-2)*24})

if __name__=='__main__':main()
