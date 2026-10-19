    .set noreorder
    .section .cache_vectors,"ax",@progbits
    .globl kr_cache_ready_entry
kr_cache_ready_entry:
    j kr_cache_menu_load
    nop
    .globl kr_cache_load_entry
kr_cache_load_entry:
    j kr_cache_menu_load
    nop
    .globl kr_cache_close_entry
kr_cache_close_entry:
    j cache_close_stub
    nop
    .globl kr_cache_name_entry
kr_cache_name_entry:
    j kr_cache_name_load
    nop
    .text
cache_close_stub:
    ori $t0,$zero,3
    bne $a1,$t0,2f
    nop
    lui $t0,0x801e
    lw $t0,0x2000($t0)
    lui $t1,0x3143
    ori $t1,$t1,0x464b
    beq $t0,$t1,1f
    nop
2:  j 0x8003a450
    nop
1:
    addiu $sp,$sp,-32
    sw $ra,24($sp)
    sw $a0,20($sp)
    lui $a0,0x8012
    ori $a0,$a0,0xc000
    lui $a1,0x8013
    ori $a1,$a1,0xd000
    jal 0x800543ac
    ori $a2,$zero,0x1000
    ori $t1,$zero,0x44
    ori $t0,$zero,0xa0
    jalr $t0
    nop
    # The copied function contains no references to the menu overlay.
    lw $a0,20($sp)
    lw $ra,24($sp)
    addiu $sp,$sp,32
    j kr_cache_field_return
    nop
