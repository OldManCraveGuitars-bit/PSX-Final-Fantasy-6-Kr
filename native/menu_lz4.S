    .set noreorder
    .text
    .globl kr_menu_unpack
kr_menu_unpack:
    # Format: https://github.com/lz4/lz4/blob/dev/doc/lz4_Block_format.md
    # Trusted build-time verified LZ4 block, prefixed by decoded byte count.
    # Source and destination never overlap. Only caller-saved registers used.
    lw $v0,0($a0)
    addiu $a0,$a0,4
    addu $v0,$v0,$a1
    ori $t4,$zero,255
sequence:
    lbu $t0,0($a0)
    addiu $a0,$a0,1
    srl $t1,$t0,4
    ori $t3,$zero,15
    bne $t1,$t3,literals
    nop
literal_length:
    lbu $t2,0($a0)
    addiu $a0,$a0,1
    beq $t2,$t4,literal_length
    addu $t1,$t1,$t2
literals:
    beqz $t1,literal_end
    nop
literal_copy:
    lbu $t2,0($a0)
    addiu $a0,$a0,1
    sb $t2,0($a1)
    addiu $t1,$t1,-1
    bnez $t1,literal_copy
    addiu $a1,$a1,1
literal_end:
    beq $a1,$v0,done
    nop
    lbu $t2,0($a0)
    lbu $t3,1($a0)
    addiu $a0,$a0,2
    sll $t3,$t3,8
    or $t2,$t2,$t3
    subu $t2,$a1,$t2
    andi $t1,$t0,15
    ori $t3,$zero,15
    bne $t1,$t3,match_copy
    addiu $t1,$t1,4
match_length:
    lbu $t3,0($a0)
    addiu $a0,$a0,1
    beq $t3,$t4,match_length
    addu $t1,$t1,$t3
match_copy:
    lbu $t3,0($t2)
    addiu $t2,$t2,1
    sb $t3,0($a1)
    addiu $t1,$t1,-1
    bnez $t1,match_copy
    addiu $a1,$a1,1
    b sequence
    nop
done:
    jr $ra
    nop
