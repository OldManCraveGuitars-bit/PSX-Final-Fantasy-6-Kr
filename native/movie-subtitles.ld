OUTPUT_ARCH(mips)
ENTRY(kr_movie_play)
SECTIONS {
    . = 0x80037800;
    .text : { *(.text .text.*) }
    .rodata : { *(.rodata .rodata.*) }
    . = 0x80037d40;
    .boost_resident : { *(.boost_resident) }
    .battle_loader : { *(.battle_loader) }
    .menu_loader : { *(.menu_loader) }
    /DISCARD/ : { *(.MIPS.abiflags .reginfo .pdr .comment .gnu.attributes) }
}
