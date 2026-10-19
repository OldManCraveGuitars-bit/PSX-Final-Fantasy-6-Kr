"""Fixed native TIM text rectangles, shared by the editor and ROM builder."""
import re


def validate_gallery_rows(rows):
    if not isinstance(rows,list):raise ValueError('갤러리 문장 목록이 필요합니다.')
    seen=set();regions={}
    for row in rows:
        if not isinstance(row,dict):raise ValueError('갤러리 항목 형식이 올바르지 않습니다.')
        key=str(row.get('id',''))
        if not key or key in seen:raise ValueError('갤러리 ID가 비었거나 중복됩니다: '+key)
        seen.add(key)
        file=row.get('file','');index=row.get('image')
        if not re.fullmatch(r'OMAKEDIR/GALLERY[1-5]\.BIN',file):raise ValueError('갤러리 원본 파일이 올바르지 않습니다.')
        limits={1:25,2:18,3:31,4:15,5:29}
        if type(index)!=int or not 0<=index<limits[int(file[-5])]:raise ValueError('갤러리 그림 번호가 범위를 벗어났습니다.')
        rect=row.get('rect',[])
        if not isinstance(rect,list) or len(rect)!=4 or any(type(v)!=int for v in rect):raise ValueError('갤러리 글자 영역은 정수 네 개가 필요합니다.')
        x,y,w,h=rect
        if not (x>=0 and y>=0 and w>=8 and h>=8 and x+w<=640 and y+h<=480):raise ValueError('갤러리 글자 영역이 그림 밖으로 나갑니다.')
        erase=row.get('erase_rects',[rect])
        if not isinstance(erase,list) or not erase:raise ValueError('갤러리 원문 지우기 영역이 필요합니다.')
        for box in erase:
            if not isinstance(box,list) or len(box)!=4 or any(type(v)!=int for v in box):raise ValueError('갤러리 지우기 영역은 정수 네 개가 필요합니다.')
            a,b,c,d=box
            if not (a>=0 and b>=0 and c>0 and d>0 and a+c<=640 and b+d<=480):raise ValueError('갤러리 지우기 영역이 그림 밖으로 나갑니다.')
        if 'erase_sample_x' in row and (type(row['erase_sample_x'])!=int or not 0<=row['erase_sample_x']<640):raise ValueError('갤러리 배경 참조 열이 올바르지 않습니다.')
        if row.get('background','white') not in ('white','black'):raise ValueError('갤러리 배경색은 흰색 또는 검은색이어야 합니다.')
        if not isinstance(row.get('source'),str) or not isinstance(row.get('translation'),str):raise ValueError('갤러리 원문과 번역이 필요합니다.')
        prior=regions.setdefault((file,index),[])
        for a,b,c,d in prior:
            if x<a+c and a<x+w and y<b+d and b<y+h:raise ValueError('갤러리 글자 영역이 겹칩니다: '+key)
        prior.append(rect)
