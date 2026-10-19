"""Stage visible END.STR cards for registration through the standalone editor."""
import json
from textcodec import ROOT
from caption_format import validate_caption_rows

# Zero-based decoded frames at 15 fps; retain each card's fade interval.
ROWS = [
    (32,72,'一体何を見つけたというのだ','대체 무엇을 찾았다는 거냐?'),
    (138,177,'死に絶えようとしている','멸망해 가는'),
    (249,290,'この世界で','이 세상에서.'),
    (2633,2690,'壊れると分かっていてなぜ創る','부서질 줄 알면서 왜 만드는 거냐?'),
    (2743,2800,'死ぬと分かっていてなぜ生きようとする','죽을 걸 알면서 왜 살려고 하는 거냐?'),
]

def main():
    rows=[r for r in json.loads((ROOT/'translations/movie-subtitles.ko.json').read_text('utf8')) if r.get('movie','OPERA')!='END']
    rows += [dict(movie='END',start_frame=a,end_frame=b,source=source,translation=text,
        evidence=f'Original MOVIE/END.STR, 15 fps, decoded frames {a}..{b-1}',status='manual')
        for a,b,source,text in ROWS]
    validate_caption_rows(rows)
    path=ROOT/'work/ending-caption-import.json'
    path.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n','utf8')
    print({'staging':str(path),'ending_cues':len(ROWS),'total_cues':len(rows)})

if __name__=='__main__':main()
