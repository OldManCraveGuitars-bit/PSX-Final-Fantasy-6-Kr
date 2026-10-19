    .set noreorder
    .set noat
    .text
    .globl kr_big_ref_case
kr_big_ref_case:
    jal kr_big_reference
    nop
    j 0x800d00e4
    nop
    .globl kr_big_original_glyph
kr_big_original_glyph:
    lui $v0,0x8003
    lbu $v0,-0x1fb5($v0)
    j 0x800d1448
    nop
    .macro WORD name,target,continuation
    .globl \name
\name:
    lhu $a0,0x12($sp)
    jal \target
    nop
    j \continuation
    nop
    .endm
    WORD kr_big_small_list_hook,kr_big_small_list,0x800d3548
    WORD kr_big_small_short_hook,kr_big_small_list,0x800d3760
    WORD kr_big_small_summon_hook,kr_big_small_list,0x800d3bf0
    WORD kr_big_small_magitek_hook,kr_big_small_magitek,0x800d3acc
    WORD kr_big_small_bushido_hook,kr_big_small_bushido,0x800d30d4
    WORD kr_big_small_menu_hook,kr_big_small_menu,0x800d5b94
    WORD kr_big_esper_attack_copy_hook,kr_big_esper_attack_copy,0x80127794
    .globl kr_big_monster_attack_source_hook
kr_big_monster_attack_source_hook:
    lhu $a0,0x10($sp)
    jal kr_big_monster_attack_source
    nop
    ori $v0,$zero,3
    sh $v0,0x14($sp)
    j 0x801408f8
    lui $s0,0x8002
