OUTPUT_ARCH(mips)
ENTRY(kr_psx_name)
SECTIONS {
    . = 0x80036c20;
    .text : { *(.text .text.*) *(.rodata .rodata.*) }
    /DISCARD/ : { *(.MIPS.abiflags .reginfo .pdr .comment .gnu.attributes) }
}
