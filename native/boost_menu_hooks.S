    .set noreorder
    .section .boost,"ax",@progbits
    .globl kr_config_magic_hook
kr_config_magic_hook:
    jal kr_config_magic
    nop
    # Native magic-order routine already saved its return address and s0..s2.
    j 0x800de9e8
    nop
