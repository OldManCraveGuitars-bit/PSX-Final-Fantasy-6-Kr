"""Fixed native boost-page text slots shared by the builder and EXE editor."""
WIDTHS={
    'hint':176,'title':160,'encounter':80,'exp':80,'gil':80,'ap':80,
    'off':24,'on':24,'controls':216,'back':216,'default':216,
    'desc_encounter':216,'desc_exp':216,'desc_gil':216,'desc_ap':216,
    'magic_recovery':48,'magic_attack':48,'magic_effect':48,
    'rank1':16,'rank2':16,'rank3':16,'cursor':8,
}
def validate_boost_rows(rows):
    if not isinstance(rows,dict) or set(rows)!=set(WIDTHS):
        raise ValueError('부스트·설정 화면의 글씨 항목이 모두 필요합니다.')
    for key,row in rows.items():
        text=row.get('translation','')
        if not isinstance(text,str) or not text.strip() or any(c in text for c in '\n\r\t{}'):
            raise ValueError('부스트 글씨는 빈칸 없는 한 줄이어야 합니다: '+key)
        if any(ord(c)<32 or c=='\u3000' for c in text):
            raise ValueError('부스트 글씨에는 반각 공백을 사용하세요: '+key)
        if sum(4 if c==' ' else 8 for c in text)>WIDTHS[key]:
            raise ValueError('부스트 화면의 고정 칸을 넘습니다: '+key)
