OUTPUT_ARCH(mips)
ENTRY(kr_swdtech_name)
SECTIONS {
 . = 0x8019d200;
 .text : { *(.text .text.*) }
 .rodata : { *(.rodata .rodata.*) }
 .data : { *(.data .data.*) }
 .bss : { *(.bss .bss.* COMMON) }
 /DISCARD/ : { *(.MIPS.abiflags .reginfo .pdr .comment .gnu.attributes) }
}
