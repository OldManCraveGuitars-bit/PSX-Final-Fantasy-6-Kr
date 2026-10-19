"""Read-only R3000 disassembly and reference search for the original overlays."""
import argparse
from pathlib import Path
from capstone import Cs, CS_ARCH_MIPS, CS_MODE_MIPS32, CS_MODE_LITTLE_ENDIAN
from textcodec import ROOT

FILES={
    'menu':('work/decompressed/HAR/HARATA.PAC',0x800c8000),
    'field':('work/decompressed/NAR/NARITA.PAC',0x800c8000),
    'battle':('work/decompressed/BTL/BATTLE.PAC',0x800c8000),
    'world':('work/decompressed/OGA/OGATA.PAC',0x800c8000),
    'exe':('work/extracted/SLPM_861.98',0x80037800),
}
def instructions(kind):
    file,base=FILES[kind]
    data=(ROOT/file).read_bytes()
    md=Cs(CS_ARCH_MIPS,CS_MODE_MIPS32|CS_MODE_LITTLE_ENDIAN)
    md.skipdata=True
    return list(md.disasm(data,base))
def main():
    p=argparse.ArgumentParser();p.add_argument('kind',choices=FILES)
    p.add_argument('start',nargs='?',type=lambda s:int(s,0));p.add_argument('end',nargs='?',type=lambda s:int(s,0))
    p.add_argument('--find');p.add_argument('--context',type=int,default=4)
    a=p.parse_args();rows=instructions(a.kind)
    selected=set()
    for i,r in enumerate(rows):
        if a.find and a.find in r.op_str:
            selected.update(range(max(0,i-a.context),min(len(rows),i+a.context+1)))
        elif not a.find and a.start<=r.address<(a.end or a.start+0x100):selected.add(i)
    prev=-2
    for i in sorted(selected):
        if i!=prev+1:print('...')
        r=rows[i];print(f'{r.address:08x}: {r.bytes.hex()}  {r.mnemonic:8s} {r.op_str}');prev=i
if __name__=='__main__':main()
