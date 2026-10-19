OUTPUT_ARCH(mips)
ENTRY(kr_upload_small)
SECTIONS {
    . = 0x8016e000;
    .text : { *(.text .text.*) }
    .rodata : { *(.rodata .rodata.*) }
    .data : { *(.data .data.*) }
    .bss : { *(.bss .bss.* COMMON) }
    . = 0x8019f000;
    .bigtext : { *(.bigtext) }
    . = 0x8019f400;
    .boost : { *(.boost) *(.boost_data) *(.boost_state) }
    /DISCARD/ : { *(.MIPS.abiflags .reginfo .pdr .comment .gnu.attributes) }
}
