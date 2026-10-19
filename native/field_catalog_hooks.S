    .set noreorder
    .set noat
    .text
    .globl kr_boost_new_game
kr_boost_new_game:
    # The native new-game initializer does not clear the extended save header.
    # Invalidate only the booster tag, preserving the name-cache format.
    lui $v0,0x8003
    sw $zero,0x0708($v0)
    sw $zero,0x6008($v0)
    addiu $sp,$sp,-0x28
    j 0x801008a4
    addiu $a0,$sp,0x10

    .globl kr_field_item_hook
kr_field_item_hook:
    addiu $sp,$sp,-0x60
    sw $a0,0x14($sp)
    ori $a0,$zero,0
    j 1f
    nop
    .globl kr_field_spell_hook
kr_field_spell_hook:
    addiu $sp,$sp,-0x60
    sw $a0,0x14($sp)
    ori $a0,$zero,1
1:
    sw $v1,0x10($sp)
    sw $a1,0x18($sp)
    sw $a2,0x1c($sp)
    sw $a3,0x20($sp)
    sw $t0,0x24($sp)
    sw $t1,0x28($sp)
    sw $t2,0x2c($sp)
    sw $t3,0x30($sp)
    sw $t4,0x34($sp)
    sw $t5,0x38($sp)
    sw $t6,0x3c($sp)
    sw $t7,0x40($sp)
    sw $t8,0x44($sp)
    sw $t9,0x48($sp)
    sw $ra,0x4c($sp)
    jal kr_field_catalog
    nop
    lw $v1,0x10($sp)
    lw $a0,0x14($sp)
    lw $a1,0x18($sp)
    lw $a2,0x1c($sp)
    lw $a3,0x20($sp)
    lw $t0,0x24($sp)
    lw $t1,0x28($sp)
    lw $t2,0x2c($sp)
    lw $t3,0x30($sp)
    lw $t4,0x34($sp)
    lw $t5,0x38($sp)
    lw $t6,0x3c($sp)
    lw $t7,0x40($sp)
    lw $t8,0x44($sp)
    lw $t9,0x48($sp)
    lw $ra,0x4c($sp)
    addiu $sp,$sp,0x60
    j 0x80103760
    nop
