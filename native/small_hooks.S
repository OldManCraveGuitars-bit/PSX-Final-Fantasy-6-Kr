    .set noreorder
    .set noat
    .text
    .macro LABEL_HOOK name, frame, raslot, continuation, target
    .globl \name
\name:
    addiu $sp,$sp,-16
    sw $t0,8($sp)
    sw $t1,12($sp)
    lui $t0,0x8003
    lbu $t1,-0x1f17($t0)
    nop
    sll $t1,$t1,16
    lbu $t0,-0x1f18($t0)
    nop
    sll $t0,$t0,8
    or $t1,$t1,$t0
    lui $t0,0x8003
    lbu $t0,-0x1f19($t0)
    nop
    or $t1,$t1,$t0
    lui $t0,0x8000
    or $t1,$t1,$t0
    lbu $t0,2($t1)
    nop
    addiu $t0,$t0,-0x1b
    beqz $t0,1f
    nop
    addiu $t0,$t0,6
    beqz $t0,1f
    nop
    addiu $t0,$t0,1
    beqz $t0,1f
    nop
    addiu $t0,$t0,-1
    addiu $t0,$t0,-1
    beqz $t0,1f
    nop
    addiu $t0,$t0,-1
    beqz $t0,1f
    nop
    addiu $t0,$t0,-1
    beqz $t0,1f
    nop
    addiu $t0,$t0,0x18
    sltiu $t0,$t0,0xe0
    bnez $t0,2f
    nop
    lbu $t0,3($t1)
    nop
    addiu $t0,$t0,-0x17
    beqz $t0,1f
    nop
2:
    lw $t0,8($sp)
    lw $t1,12($sp)
    addiu $sp,$sp,16
    addiu $sp,$sp,-\frame
    sw $ra,\raslot($sp)
    j \continuation
    nop
1:  lw $t0,8($sp)
    lw $t1,12($sp)
    addiu $sp,$sp,16
    j \target
    nop
    .endm
    LABEL_HOOK kr_label_hook,0x38,0x34,0x800f5ae8,kr_copy_label
    LABEL_HOOK kr_rich_label_hook,0x28,0x24,0x800f5fd0,kr_copy_rich_label

    .globl kr_sprite_begin
kr_sprite_begin:
    addiu $sp,$sp,-0x58
    sw $s6,0x48($sp)
    /* The caller keeps native texture X in s6 and Y at 28(sp).
       Retain that page for the unmodified canvas sprites between letters. */
    srl $v0,$s6,6
    andi $v0,$v0,15
    lhu $v1,0x80($sp)
    nop
    andi $v1,$v1,0x100
    srl $v1,$v1,4
    or $v0,$v0,$v1
    sw $v0,0x1c($sp)
    j 0x8012014c
    nop

    .macro SPRITE_PAGE name, continuation
    .globl \name
\name:
    andi $v0,$a2,0x8000
    beqz $v0,9f
    nop
    lw $v1,0x1c($sp)
    ori $v0,$zero,8
    beq $v0,$v1,9f
    nop
    lui $v0,0x8013
    lhu $t2,-0x1c68($v0)
    nop
    sltiu $v0,$t2,1024
    beqz $v0,9f
    nop
    lui $v0,0x8007
    lbu $v0,-0x3f2c($v0)
    sll $t2,$t2,4
    andi $v0,$v0,1
    sll $v0,$v0,14
    addu $t2,$t2,$v0
    lui $a0,0x801a
    addu $a0,$a0,$t2
    /* GPU list order: primary page, letter, original page, old list. */
    lw $v0,0($t1)
    lui $t3,0x00ff
    ori $t3,$t3,0xffff
    and $t2,$v0,$t3
    lui $at,0x0100
    or $t2,$t2,$at
    sw $t2,8($a0)
    lui $t2,0xe100
    or $v1,$v1,$t2
    sw $v1,12($a0)
    lui $v1,0xff00
    and $v0,$v0,$v1
    addiu $t2,$a0,8
    and $t2,$t2,$t3
    or $v0,$v0,$t2
    sw $v0,0($t1)
    and $v0,$t1,$t3
    or $v0,$v0,$at
    sw $v0,0($a0)
    lui $v0,0xe100
    ori $v0,$v0,8
    sw $v0,4($a0)
    move $v0,$t6
    andi $t2,$a2,0x2000
    beqz $t2,8f
    nop
    lw $v0,0x6c($sp)
    lw $t2,0x70($sp)
    nop
    addu $v0,$v0,$t2
    sll $v0,$v0,2
    addu $v0,$v0,$s6
8:  lw $t2,0x70($v0)
    and $a0,$a0,$t3
    and $t2,$t2,$v1
    or $t2,$t2,$a0
    sw $t2,0x70($v0)
9:  addiu $t0,$t0,0x14
    lui $v0,0x8013
    j \continuation
    nop
    .endm
    SPRITE_PAGE kr_sprite_page_1,0x801204a8
    SPRITE_PAGE kr_sprite_page_2,0x80120790

    .globl kr_row_start_1
kr_row_start_1:
    srl $t5,$a0,3
    move $t7,$zero
    sw $zero,0x24($sp)
    j 0x80120294
    nop
    .globl kr_row_start_2
kr_row_start_2:
    srl $t5,$a0,3
    move $t7,$zero
    sw $zero,0x24($sp)
    j 0x80120588
    nop

    .macro CELL_HOOK name, normal, skip
    .globl \name
\name:
    ori $v0,$zero,0x8ffe
    beq $a2,$v0,2f
    nop
    ori $v0,$zero,0xcfff
    beq $a2,$v0,3f
    nop
    andi $v1,$a2,0xffff
    beqz $v1,3f
    nop
    j \normal
    nop
2:  lw $v0,0x24($sp)
    nop
    addiu $v0,$v0,-4
    sw $v0,0x24($sp)
    j \skip
    nop
3:  sw $zero,0x24($sp)
    j \skip
    nop
    .endm
    CELL_HOOK kr_cell_1,0x80120350,0x801204bc
    CELL_HOOK kr_cell_2,0x8012063c,0x801207a4

    .globl kr_x_1
kr_x_1:
    lw $s1,0x24($sp)
    addu $a0,$s4,$v0
    addu $a0,$a0,$s1
    andi $v0,$a2,0x200
    j 0x80120388
    nop
    .globl kr_x_2
kr_x_2:
    lw $s4,0x24($sp)
    addu $a0,$s1,$v0
    addu $a0,$a0,$s4
    andi $v0,$a2,0x200
    j 0x80120674
    nop

    .globl kr_name_keys_hook
kr_name_keys_hook:
    addiu $sp,$sp,-0x60
    sw $v0,0x10($sp)
    sw $v1,0x14($sp)
    sw $a0,0x18($sp)
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
    mfhi $t0
    mflo $t1
    sw $t0,0x54($sp)
    sw $t1,0x58($sp)
    jal kr_name_keys
    nop
    lw $t0,0x54($sp)
    lw $t1,0x58($sp)
    mthi $t0
    mtlo $t1
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
    bnez $v0,1f
    lw $v0,0x10($sp)
    addiu $sp,$sp,0x60
    j 0x800fd760
    nop
1:  addiu $sp,$sp,0x60
    j 0x800fd734
    nop
