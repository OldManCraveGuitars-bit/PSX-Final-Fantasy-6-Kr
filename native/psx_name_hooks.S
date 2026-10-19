    .set noreorder
    .set noat
    .text
    .globl kr_psx_read_complete_hook
kr_psx_read_complete_hook:
    addiu $sp,$sp,-32
    sw $ra,28($sp)
    sw $a0,16($sp)
    jal kr_psx_read_complete
    nop
    lw $a0,16($sp)
    lw $ra,28($sp)
    addiu $sp,$sp,32
    addiu $sp,$sp,-0x40
    sw $s0,0x28($sp)
    j 0x800d656c
    nop

/* Font primitives are recycled for every kind of small text. Restore the
 * original texture page whenever the original renderer emits a character;
 * the name wrapper then changes only the letters it has just emitted. */
    .globl kr_psx_glyph_page_reset
kr_psx_glyph_page_reset:
    lw $v0,4($t5)
    addiu $at,$zero,-16
    and $v0,$v0,$at
    ori $v0,$v0,7
    sw $v0,4($t5)
    lw $v0,16($t5)
    nop
    and $v0,$v0,$at
    ori $v0,$v0,7
    sw $v0,16($t5)
    j 0x800cb920
    lhu $v0,4($a1)

/* Native printf uses character columns plus a pixel offset. A space keeps
 * the original column counter and subtracts half a cell from that offset. */
    .globl kr_psx_half_space
kr_psx_half_space:
    nop                         /* load delay from the hook's delay slot */
    addiu $v0,$v0,1
    sh $v0,0x18($a1)
    lh $at,0x24($a1)
    nop
    addiu $at,$at,-4
    sh $at,0x24($a1)
    j 0x800cb940
    nop

    .globl kr_psx_literal_half_space
kr_psx_literal_half_space:
    nop                         /* load delay from the hook's delay slot */
    addiu $v0,$v0,1
    sh $v0,0x18($s2)
    lh $at,0x24($s2)
    nop
    addiu $at,$at,-4
    sh $at,0x24($s2)
    j 0x800cbfe8
    nop
