SECTIONS {
 . = 0x801dceb0;
 .text : { *(.text*) *(.rodata*) }
 /DISCARD/ : { *(.comment) *(.note*) *(.reginfo) *(.MIPS.abiflags) *(.pdr) *(.eh_frame*) }
}
