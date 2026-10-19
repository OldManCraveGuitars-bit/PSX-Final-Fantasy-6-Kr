"""Execute the compiled caption renderer and memory-preserving movie wrapper."""
import json,struct
from unicorn import Uc,UC_ARCH_MIPS,UC_MODE_MIPS32,UC_MODE_LITTLE_ENDIAN,UC_HOOK_CODE
from unicorn.mips_const import *
from textcodec import ROOT
from movie_subtitles import caption_data,msf_word

def main():
    report=json.loads((ROOT/'analysis/movie-subtitles-runtime.json').read_text('utf8'))
    expected_reads=[struct.pack('<I',msf_word(report['movies'][movie]['bank_lba'])).hex() for movie in ['OPERA','OPEN','END']]
    syms=report['symbols'];u=Uc(UC_ARCH_MIPS,UC_MODE_MIPS32|UC_MODE_LITTLE_ENDIAN)
    u.mem_map(0,0x200000);u.mem_write(0x37800,(ROOT/'work/movie-subtitles.bin').read_bytes())
    for addr in [0x5ab0c,0x5adb8,0x4d2d8,0x460c0,0x470b8,0x59820,syms['kr_movie_original']&0x1fffff,0x37ff0]:
        u.mem_write(addr,struct.pack('<II',0x03e00008,0x00001021))
    data=caption_data([{'start_frame':15,'end_frame':30,'translation':'별도 자막 출력 확인'},
        {'start_frame':30,'end_frame':45,'translation':'두 줄 자막\n둘째 줄 확인'}])
    renders=[];reads=[];movies=[]
    def hook(cpu,address,size,user):
        phys=address&0x1fffff
        if phys==0x5adb8:
            rect=struct.unpack('<4h',cpu.mem_read(cpu.reg_read(UC_MIPS_REG_A0)&0x1fffff,8))
            pixels=bytes(cpu.mem_read(cpu.reg_read(UC_MIPS_REG_A1)&0x1fffff,13440))
            renders.append((rect,pixels))
        elif phys==0x4d2d8:
            assert cpu.reg_read(UC_MIPS_REG_A0)==0x80033000
            assert cpu.reg_read(UC_MIPS_REG_A1)==2
            msf=bytes(cpu.mem_read(cpu.reg_read(UC_MIPS_REG_A2)&0x1fffff,4));assert msf.hex() in expected_reads
            cpu.mem_write(0x33000,bytes(data));reads.append(msf.hex())
        elif phys==(syms['kr_movie_original']&0x1fffff):
            movies.append(tuple(cpu.reg_read(r) for r in [UC_MIPS_REG_A0,UC_MIPS_REG_A1,UC_MIPS_REG_A2,UC_MIPS_REG_A3]))
    u.hook_add(UC_HOOK_CODE,hook)
    def invoke(fn,args):
        u.reg_write(UC_MIPS_REG_SP,0x801ffff0);u.reg_write(UC_MIPS_REG_RA,0x801ffffc)
        for reg,value in zip([UC_MIPS_REG_A0,UC_MIPS_REG_A1,UC_MIPS_REG_A2,UC_MIPS_REG_A3],args):u.reg_write(reg,value)
        u.emu_start(syms[fn],0x801ffffc,count=1000000)
        assert u.reg_read(UC_MIPS_REG_PC)==0x801ffffc and u.reg_read(UC_MIPS_REG_SP)==0x801ffff0
    u.mem_write(0x33000,bytes(data));u.mem_write(0x33fe0,struct.pack('<II',0x80037ff0,0x80020000))
    for frame,expected in [(0,0),(14,0),(15,2),(29,2),(30,4),(44,4),(45,0),(3000,0)]:
        renders.clear();u.mem_write(0x33fe8,struct.pack('<I',frame+1));invoke('kr_movie_caption',[0,1])
        assert len(renders)==expected
        if expected:
            assert [x[0] for x in renders]==([(0,220,480,14),(0,476,480,14)] if expected==2 else
                [(0,206,480,14),(0,462,480,14),(0,220,480,14),(0,476,480,14)])
            assert renders[0][1]==renders[1][1] and set(renders[0][1])=={0,255}
            on=[i//3%320 for i,x in enumerate(renders[0][1]) if x]
            assert min(on)>=80 and max(on)<=240
    u.mem_write(0x6c054,struct.pack('<I',syms['kr_movie_caption']))
    u.mem_write(0x33fe8,bytes(8));u.mem_write(0x2000c,struct.pack('<I',2941))
    for frame in [1,2,3,2940]:
        previous=struct.unpack('<I',u.mem_read(0x33fec,4))[0]
        u.mem_write(0x21008,struct.pack('<I',frame))
        u.reg_write(UC_MIPS_REG_A0,0x80021000);u.reg_write(UC_MIPS_REG_S2,0x80020000)
        u.emu_start(syms['kr_movie_frame'],0x80045df4,count=100)
        assert tuple(struct.unpack('<II',u.mem_read(0x33fe8,8)))==(previous,frame)
        assert u.reg_read(UC_MIPS_REG_V0)==frame and u.reg_read(UC_MIPS_REG_V1)==2941
    u.mem_write(0x6c054,bytes(4));before_meta=bytes(u.mem_read(0x33fe8,8))
    u.emu_start(syms['kr_movie_frame'],0x80045df4,count=100)
    assert bytes(u.mem_read(0x33fe8,8))==before_meta,'Unrelated movie changed caption state'
    before=bytes((i*31+17)&255 for i in range(18432));u.mem_write(0x33000,before)
    u.mem_write(0x6c054,struct.pack('<I',0x80037ff0));u.mem_write(0x20000,struct.pack('<I',0x80021000))
    u.mem_write(0x21000,bytes.fromhex('21156000'));invoke('kr_movie_play',[0x80020000,0,0,0])
    assert bytes(u.mem_read(0x33000,18432))==before
    assert struct.unpack('<I',u.mem_read(0x6c054,4))[0]==0x80037ff0
    assert reads==expected_reads[:1] and len(movies)==1
    u.mem_write(0x21000,bytes.fromhex('07390400'));invoke('kr_movie_play',[0x80020000,0,0,0])
    assert reads==expected_reads[:2] and bytes(u.mem_read(0x33000,18432))==before
    u.mem_write(0x21000,struct.pack('<I',msf_word(63743)));invoke('kr_movie_play',[0x80020000,0,0,0])
    assert reads==expected_reads and bytes(u.mem_read(0x33000,18432))==before
    assert struct.unpack('<I',u.mem_read(0x6c054,4))[0]==0x80037ff0
    u.mem_write(0x21000,bytes.fromhex('00000000'));invoke('kr_movie_play',[0x80020000,1,2,3])
    assert len(reads)==3 and movies[-1]==(0x80020000,1,2,3)
    result={'native_frame_boundary_cases':8,'native_scratch_restore_bytes':18432,'unrelated_movie_passthrough':True,
        'independent_movie_banks':['OPERA','OPEN','END'],'maximum_rows':2,'two_rows_native_GPU_cases':2,
        'STR_frame_number_pipeline_cases':5,'STR_frame_number_origin':'1-based header converted to zero-based cue frames',
        'font':'Galmuri9','glyph_cell':[12,12],'space_pixels':6,'physical_movie_verification':'pending','lyric_alignment':'pending'}
    (ROOT/'analysis/movie-subtitles-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n','utf8')
    print(result)

if __name__=='__main__':main()
