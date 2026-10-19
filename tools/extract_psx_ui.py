"""Extract the PlayStation-only message font and its verified pointer table."""
import json,struct
from textcodec import ROOT

# Read from the game's own ALLTIM texture, 21 glyphs per row.
ROWS=[
 'あ 愛 最 初 か ら ゲ ー ム を は じ め ま す 。 メ モ リ カ ド',
 'が 入 っ て い せ ん ！ こ の だ と 新 規 セ ブ で き よ ろ し',
 '？ に 空 ロ ッ ク り や く 始 る フ ァ イ ル デ タ 呼 び 出 E',
 'M P T Y ナ ン ジ Ⅵ チ ェ コ ト ラ 抜 差 な 下 さ 選 択 壊',
 'れ 事 来 え 失 敗 た … ば 一 時 保 存 上 書 ォ マ 別 、 管 理',
 '画 面 不 要 消 も O K プ レ シ ス テ そ う 本 当 ね ぱ 1 2',
 '既 更 作 成 お け 見 必 「 」 項 目 追 加 表 示 中 何 観 楽 み',
 'つ 枚',
]
CHARACTERS=[c for row in ROWS for c in row.split()]
assert len(CHARACTERS)==149

def main():
    data=(ROOT/'work/decompressed/DEODIR/DEO.PAC').read_bytes()
    rows=[];table=0x1c194
    for identifier in range(74):
        address=struct.unpack_from('<I',data,table+identifier*4)[0];offset=address-0x800c8000
        assert 0x1b454<=offset<0x1c194
        p=offset;glyphs=[];source=[]
        while (c:=struct.unpack_from('<H',data,p)[0])!=0xffff:
            p+=2;glyphs.append(c)
            if c==0x8000:source.append('\n')
            elif c<len(CHARACTERS):source.append(CHARACTERS[c])
            else:raise ValueError(('Unknown PSX UI glyph',c,identifier))
        rows.append({'id':identifier,'source':''.join(source).rstrip('\n'),'offset':offset,
            'pointer_offset':table+identifier*4,'original_hex':data[offset:p+2].hex(),'glyphs':glyphs})
    (ROOT/'analysis/psx-ui-messages-original.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n','utf8')
    print('\n'.join(str(row['id'])+': '+row['source'].replace('\n',' / ') for row in rows))

if __name__=='__main__':main()
