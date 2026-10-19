OUTPUT_ARCH(mips)
ENTRY(kr_menu_unpack)
SECTIONS {
    . = 0x80037680;
    .text : { *(.text) }
    /DISCARD/ : { *(.MIPS.abiflags .reginfo .pdr .comment .gnu.attributes) }
}
