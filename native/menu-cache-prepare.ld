OUTPUT_ARCH(mips)
ENTRY(kr_cache_prepare_bootstrap)
SECTIONS {
    . = 0x8012c000;
    .prepare : { *(.text .text.*) *(.rodata .rodata.*) *(.data .data.*) }
    . = 0x801c5c00;
    .bootstrap : { *(.bootstrap) }
    /DISCARD/ : { *(.MIPS.abiflags .reginfo .pdr .comment .gnu.attributes) }
}
