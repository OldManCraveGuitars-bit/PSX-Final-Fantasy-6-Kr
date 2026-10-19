    .set noreorder
    .set noat
    .text
    .globl kr_omake_original_printf_glyph
kr_omake_original_printf_glyph:
    lui $a1,0x8010
    lw $a1,-0x6984($a1)
    j 0x800d9bb0
    nop
    .globl kr_omake_printf_next_hook
kr_omake_printf_next_hook:
    andi $a0,$a0,0xff
    ori $v0,$zero,32
    beq $a0,$v0,3f
    nop
    sltiu $v0,$a0,1
    bnez $v0,1f
    nop
    sltiu $v0,$a0,9
    beqz $v0,1f
    nop
    lbu $a1,1($s0)
    nop
    sltiu $v0,$a1,0x80
    bnez $v0,1f
    nop
    jal kr_omake_printf_ref
    addiu $s0,$s0,1
    j 0x800da444
    nop
1:  ori $v0,$zero,32
    j 0x800da3e4
    nop
3:  jal kr_omake_printf_glyph
    nop
    j 0x800da444
    nop
    .globl kr_omake_original_small_glyph
kr_omake_original_small_glyph:
    addiu $sp,$sp,-0x30
    sw $s3,0x1c($sp)
    j 0x800dc218
    nop
    .globl kr_omake_original_small_text
kr_omake_original_small_text:
    lui $v0,0x8010
    lw $v0,-0x6984($v0)
    j 0x800dc428
    nop
    .globl kr_omake_wide_lookup_hook
kr_omake_wide_lookup_hook:
    sw $a1,0($sp)
    sw $a2,4($sp)
    sw $a0,8($sp)
    move $a0,$a3
    jal kr_omake_get_text
    nop
    move $s0,$v0
    lw $a1,0($sp)
    lw $a2,4($sp)
    lw $a0,8($sp)
    j 0x800e0dfc
    nop
    .globl kr_omake_small_next_hook
kr_omake_small_next_hook:
    lbu $a2,0($s0)
    nop
    sltiu $v0,$a2,0x10
    bnez $v0,1f
    nop
    sltiu $v0,$a2,0x20
    beqz $v0,1f
    nop
    addiu $a2,$a2,-0x10
    sll $a2,$a2,7
    lbu $v0,1($s0)
    nop
    andi $v0,$v0,0x7f
    or $a2,$a2,$v0
    ori $a2,$a2,0x1000
    addiu $s0,$s0,1
    j 0x800dc4ac
    nop
1:  j 0x800dc49c
    nop
    .globl kr_omake_small_advance_hook
kr_omake_small_advance_hook:
    lbu $t0,-1($s0)
    addiu $s2,$s2,8
    lui $t1,0x8010
    lw $t1,-0x6c($t1)
    nop
    bnez $t1,1f
    nop
    addiu $t0,$t0,-32
    bnez $t0,1f
    nop
    addiu $s2,$s2,-4
1:  bnez $v0,2f
    nop
    j 0x800dc4e8
    nop
2:  j 0x800dc494
    nop
    .globl kr_omake_wide_glyph_hook
kr_omake_wide_glyph_hook:
    bnez $a0,1f
    nop
    lui $v0,0x800f
    lhu $v1,0x7de8($v0)
    nop
    addiu $v1,$v1,6
    jr $ra
    sh $v1,0x7de8($v0)
1:  lui $v1,0x800f
    lhu $v1,0x7e06($v1)
    j 0x800e0ad8
    nop
