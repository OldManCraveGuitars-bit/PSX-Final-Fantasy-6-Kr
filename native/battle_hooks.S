    .set noreorder
    .set noat
    .text
    .globl kr_battle_draw
kr_battle_draw:
    addiu $sp,$sp,-0x30
    sw $a0,0x10($sp)
    sw $a1,0x14($sp)
    sw $a2,0x18($sp)
    sw $a3,0x1c($sp)
    sw $ra,0x20($sp)
    jal kr_battle_upload
    nop
    lw $a0,0x10($sp)
    lw $a1,0x14($sp)
    lw $a2,0x18($sp)
    lw $a3,0x1c($sp)
    lw $ra,0x20($sp)
    addiu $sp,$sp,0x30
    addiu $sp,$sp,-0x20
    move $t3,$a1
    j 0x80156828
    nop

    .macro WORD name, target, continuation
    .globl \name
\name:
    lhu $a0,0x12($sp)
    jal \target
    nop
    j \continuation
    nop
    .endm
    WORD kr_battle_monster_hook,kr_battle_monster,0x800d5478
    WORD kr_battle_command_hook,kr_battle_command,0x800d56dc
    WORD kr_battle_spell_list_hook,kr_battle_spell_list,0x800d3548
    WORD kr_battle_spell_short_hook,kr_battle_spell_short,0x800d3760
    WORD kr_battle_spell_menu_hook,kr_battle_spell_menu,0x800d5b94
    WORD kr_battle_item_list_hook,kr_battle_item_list,0x800d3248
    WORD kr_battle_item_menu_hook,kr_battle_item_menu,0x800d595c
    WORD kr_battle_monster_list_hook,kr_battle_monster_list,0x800d39a8

    .globl kr_battle_row_1
kr_battle_row_1:
    lui $v0,0x801a
    sw $zero,-0x485c($v0)
    move $t8,$zero
    andi $v0,$a0,0x1f
    j 0x801568bc
    nop
    .globl kr_battle_row_2
kr_battle_row_2:
    lui $v0,0x801a
    sw $zero,-0x485c($v0)
    srl $t6,$a0,3
    move $t8,$zero
    j 0x80156b98
    nop

    .macro CELL name, normal, skip
    .globl \name
\name:
    ori $v0,$zero,0x8ffe
    beq $t0,$v0,2f
    nop
    ori $v0,$zero,0x21ff
    beq $t0,$v0,3f
    nop
    ori $v0,$zero,0x29ff
    beq $t0,$v0,3f
    nop
    ori $v0,$zero,0x01ee
    beq $t0,$v0,3f
    nop
    beqz $t0,3f
    nop
    andi $v1,$t0,0xffff
    j \normal
    nop
2:  lui $v0,0x801a
    lw $v1,-0x485c($v0)
    nop
    addiu $v1,$v1,-4
    sw $v1,-0x485c($v0)
    j \skip
    nop
3:  lui $v0,0x801a
    sw $zero,-0x485c($v0)
    j \skip
    nop
    .endm
    CELL kr_battle_cell_1,0x80156934,0x80156ae0
    CELL kr_battle_cell_2,0x80156bfc,0x80156d40

    .macro XPOS name, normal
    .globl \name
\name:
    lui $v1,0x801a
    lw $v1,-0x485c($v1)
    addu $a0,$s2,$v0
    addu $a0,$a0,$v1
    andi $v1,$t0,0xf
    j \normal
    nop
    .endm
    XPOS kr_battle_x_1,0x8015695c
    XPOS kr_battle_x_2,0x80156c24

    .macro COLOR name, continuation, kind
    .globl \name
\name:
    lbu $v1,0x3b96($at)
    nop
    addiu $v1,$v1,-0x8f
    beqz $v1,1f
    nop
    addiu $v1,$v1,0x8f
    andi $v1,$v1,0x83
    andi $v0,$v0,0xfc
    or $v0,$v0,$v1
    sb $v0,0x3b96($at)
1:
    .if \kind == 1
    lhu $v0,0x12($sp)
    .else
    lbu $v1,0($a0)
    .endif
    j \continuation
    nop
    .endm
    COLOR kr_battle_name_color_1,0x800f90dc,1
    COLOR kr_battle_name_color_2,0x800f92a4,2

    .globl kr_battle_frame
kr_battle_frame:
    sh $v0,0x6be4($at)
    lui $at,0x801a
    sw $zero,-0x4854($at)
    j 0x801516ec
    lui $v1,0x8003

    /* Only translated letters use page 11. Native canvas sprites retain
       page 26. Each pair belongs to one native sprite and one draw buffer. */
    .macro PAGE name, advance, continuation
    .globl \name
\name:
    andi $v0,$t0,0x8000
    beqz $v0,9f
    nop
    lui $at,0x801a
    lw $v0,-0x4854($at)
    nop
    andi $v0,$v0,0x7fff
    sltiu $v1,$v0,512
    beqz $v1,9f
    nop
    lw $v1,-0x4854($at)
    nop
    addiu $v1,$v1,1
    sw $v1,-0x4854($at)
    sll $v0,$v0,4
    lui $v1,0x8007
    lw $v1,-0x3f2c($v1)
    nop
    andi $v1,$v1,1
    sll $v1,$v1,13
    addu $v0,$v0,$v1
    lui $v1,0x801e
    ori $v1,$v1,0x0800
    addu $v1,$v1,$v0
    /* a0 still points at the original ordering-list head. */
    lw $v0,0($t1)
    lui $at,0x00ff
    ori $at,$at,0xffff
    and $v0,$v0,$at
    lui $at,0x0100
    or $v0,$v0,$at
    sw $v0,8($v1)
    lui $v0,0xe100
    ori $v0,$v0,26
    sw $v0,12($v1)
    addiu $v0,$v1,8
    lui $at,0x00ff
    ori $at,$at,0xffff
    and $v0,$v0,$at
    lui $at,0x0400
    or $v0,$v0,$at
    sw $v0,0($t1)
    lui $at,0x00ff
    ori $at,$at,0xffff
    and $v0,$t1,$at
    lui $at,0x0100
    or $v0,$v0,$at
    sw $v0,0($v1)
    lui $v0,0xe100
    ori $v0,$v0,11
    sw $v0,4($v1)
    lui $at,0x00ff
    ori $at,$at,0xffff
    and $v1,$v1,$at
    lw $v0,0($a0)
    lui $at,0xff00
    and $v0,$v0,$at
    or $v0,$v0,$v1
    sw $v0,0($a0)
9:  addiu \advance,\advance,0x14
    lui $v0,0x8019
    j \continuation
    nop
    .endm
    PAGE kr_battle_page_1,$t2,0x80156acc
    PAGE kr_battle_page_2,$a1,0x80156d2c
