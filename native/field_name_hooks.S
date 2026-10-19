    .set noreorder
    .set noat
    .section .name_hooks,"ax",@progbits
    .globl kr_field_hchar
kr_field_hchar:
    addiu $sp,$sp,-0x60
    sw $a0,0x18($sp)
    ori $a0,$zero,2
    j 1f
    nop
    .globl kr_field_char
kr_field_char:
    addiu $sp,$sp,-0x60
    sw $a0,0x18($sp)
    ori $a0,$zero,0xf0
1:
    sw $v1,0x14($sp)
    sw $a1,0x1c($sp)
    sw $a2,0x20($sp)
    sw $a3,0x24($sp)
    sw $t0,0x28($sp)
    sw $t1,0x2c($sp)
    sw $t2,0x30($sp)
    sw $t3,0x34($sp)
    sw $t4,0x38($sp)
    sw $t5,0x3c($sp)
    sw $t6,0x40($sp)
    sw $t7,0x44($sp)
    sw $t8,0x48($sp)
    sw $t9,0x4c($sp)
    sw $ra,0x50($sp)
    lbu $v0,0x70($sp)
    nop
    subu $a0,$v0,$a0
    jal kr_field_name
    nop
    srl $t0,$v0,8
    sh $t0,0x74($sp)
    andi $t0,$v0,0xff
    sh $t0,0x72($sp)
    sh $zero,0x70($sp)
    lw $v1,0x14($sp)
    lw $a0,0x18($sp)
    lw $a1,0x1c($sp)
    lw $a2,0x20($sp)
    lw $a3,0x24($sp)
    lw $t0,0x28($sp)
    lw $t1,0x2c($sp)
    lw $t2,0x30($sp)
    lw $t3,0x34($sp)
    lw $t4,0x38($sp)
    lw $t5,0x3c($sp)
    lw $t6,0x40($sp)
    lw $t7,0x44($sp)
    lw $t8,0x48($sp)
    lw $t9,0x4c($sp)
    lw $ra,0x50($sp)
    addiu $sp,$sp,0x60
    j 0x8010349c
    nop
