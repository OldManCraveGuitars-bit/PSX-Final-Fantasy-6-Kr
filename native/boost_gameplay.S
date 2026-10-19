    .set noreorder
    .section .boost_resident,"ax",@progbits
    # Live flags are in the reserved eight-byte KRN1 save header. Never read
    # the preview cache: loading another save must change all four options.
    .globl kr_boost_flags
kr_boost_flags:
    lui $t0,0x8003
    lw $v1,0x0700($t0)
    lui $t1,0x314e
    ori $t1,$t1,0x524b
    bne $v1,$t1,9f
    nop
    lw $v1,0x0708($t0)
    lui $t1,0x3154
    ori $t1,$t1,0x5342
    bne $v1,$t1,9f
    nop
    lbu $v0,0x070c($t0)
    # R3000 load delay: read the full check word while the flag byte arrives.
    lw $v1,0x070c($t0)
    sltiu $t1,$v0,16
    beqz $t1,9f
    xori $t1,$v0,0xa5
    sll $t1,$t1,8
    or $t1,$t1,$v0
    bne $v1,$t1,9f
    nop
    jr $ra
    nop
9:
    jr $ra
    move $v0,$zero

    .globl kr_boost_field_check
kr_boost_field_check:
    addiu $sp,$sp,-24
    sw $ra,20($sp)
    jal kr_boost_flags
    nop
    andi $v0,$v0,1
    lw $ra,20($sp)
    bnez $v0,1f
    addiu $sp,$sp,24
    j 0x800d2748
    nop
1:
    jr $ra
    nop

    .globl kr_boost_world_check
kr_boost_world_check:
    addiu $sp,$sp,-24
    sw $ra,20($sp)
    jal kr_boost_flags
    nop
    andi $v0,$v0,1
    lw $ra,20($sp)
    bnez $v0,2f
    addiu $sp,$sp,24
    # Displaced world-check prologue, before its native stack allocation.
    lui $v0,0x8007
    lw $v0,-0x3e94($v0)
    j 0x800cdf4c
    nop
2:
    lui $t0,0x8007
    lw $t0,-0x3e98($t0)
    nop
    sh $zero,0($t0)
    jr $ra
    nop

    .macro MULTIPLY24 offset, mask
    andi $t0,$t5,\mask
    beqz $t0,1f
    nop
    lbu $t0,\offset($t4)
    lbu $t1,\offset+1($t4)
    lbu $t2,\offset+2($t4)
    sll $t1,$t1,8
    sll $t2,$t2,16
    or $t0,$t0,$t1
    or $t0,$t0,$t2
    sll $t1,$t0,2
    addu $t0,$t0,$t1
    srl $t1,$t0,24
    beqz $t1,2f
    nop
    lui $t0,0x00ff
    ori $t0,$t0,0xffff
2:
    sb $t0,\offset($t4)
    srl $t0,$t0,8
    sb $t0,\offset+1($t4)
    srl $t0,$t0,8
    sb $t0,\offset+2($t4)
1:
    .endm

    # One invocation per native victory, after summing defeated monsters and
    # before XP division, relic bonuses, learning, reward messages and caps.
    .globl kr_boost_rewards
kr_boost_rewards:
    addiu $sp,$sp,-56
    sw $ra,52($sp)
    sw $v0,16($sp)
    sw $v1,20($sp)
    sw $t0,24($sp)
    sw $t1,28($sp)
    sw $t2,32($sp)
    sw $t4,36($sp)
    sw $t5,40($sp)
    jal kr_boost_flags
    nop
    move $t5,$v0
    lui $t4,0x8002
    MULTIPLY24 0x0f35,2
    MULTIPLY24 0x0f3e,4
    andi $t0,$t5,8
    beqz $t0,3f
    lui $t4,0x8003
    lbu $t0,-0x1f05($t4)
    nop
    sll $t1,$t0,2
    addu $t0,$t0,$t1
    sltiu $t1,$t0,256
    bnez $t1,4f
    nop
    ori $t0,$zero,255
4:
    sb $t0,-0x1f05($t4)
3:
    lw $v0,16($sp)
    lw $v1,20($sp)
    lw $t0,24($sp)
    lw $t1,28($sp)
    lw $t2,32($sp)
    lw $t4,36($sp)
    lw $t5,40($sp)
    lw $ra,52($sp)
    addiu $sp,$sp,56
    # Original instructions at 80169404..8016940b.
    move $a0,$s1
    jr $ra
    lui $a1,0x8002
