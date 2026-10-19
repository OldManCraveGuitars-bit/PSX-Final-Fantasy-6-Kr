    .set noreorder
    .section .bootstrap,"ax",@progbits
    .globl kr_cache_prepare_bootstrap
kr_cache_prepare_bootstrap:
    addiu $sp,$sp,-24
    sw $ra,16($sp)
    lui $a0,0x8012
    ori $a0,$a0,0xc000
    lui $a1,0x801c
    ori $a1,$a1,0x5c80
    jal 0x800543ac
    ori $a2,$zero,0x580
    # PSX BIOS FlushCache (A0:44), before executing copied instructions.
    ori $t1,$zero,0x44
    ori $t0,$zero,0xa0
    jalr $t0
    nop
    lw $ra,16($sp)
    addiu $sp,$sp,24
    j kr_cache_preserve
    nop
