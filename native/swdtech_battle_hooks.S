    .set noreorder
    .text
    .globl kr_swdtech_battle_hook
kr_swdtech_battle_hook:
    lhu $a0,0x12($sp)
    jal kr_swdtech_battle
    nop
    beq $v0,$zero,1f
    nop
    j 0x80127794
    nop
1:
    lui $v0,0x8007
    lw $v0,-0x3e94($v0)
    j 0x801275bc
    nop
