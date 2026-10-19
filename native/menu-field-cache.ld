OUTPUT_ARCH(mips)
ENTRY(kr_cache_ready_entry)
SECTIONS {
    . = 0x8012c000;
    .cache_return : { *(.cache_return) }
    . = 0x80135000;
    .cache_main : { *(.cache_vectors) *(.text .text.*) *(.rodata .rodata.*) *(.data .data.*) }
    /DISCARD/ : { *(.MIPS.abiflags .reginfo .pdr .comment .gnu.attributes) }
}
