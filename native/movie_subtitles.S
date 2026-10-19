    .set noreorder
    .text
    .globl kr_movie_frame
kr_movie_frame:
    # The loop fetches the next STR frame before displaying the decoded frame.
    # Keep both IDs; the previous one is the frame being presented (1-based).
    lui $v0,0x8007
    lw $v0,-0x3fac($v0)
    lui $v1,%hi(kr_movie_caption)
    addiu $v1,$v1,%lo(kr_movie_caption)
    bne $v0,$v1,1f
    nop
    lui $v1,0x8003
    lw $v0,0x3fec($v1)
    nop
    sw $v0,0x3fe8($v1)
    lw $v0,8($a0)
    nop
    sw $v0,0x3fec($v1)
1:
    lw $v1,0xc($s2)
    lw $v0,8($a0)
    j 0x80045df4
    nop

    .globl kr_movie_original
kr_movie_original:
    addiu $sp,$sp,-0x38
    sw $s0,0x18($sp)
    j 0x800455fc
    nop

    .section .battle_loader,"ax",@progbits
    .globl kr_battle_data_shift
kr_battle_data_shift:
    # Both queued CD reads have completed and BATTLE.PAC is decompressed.
    # Loading the prefix directly at 197c00 corrupted the unread PAC tail.
    # A forward move is safe for the overlapping source/destination ranges.
    addiu $sp,$sp,-16
    sw $v0,0($sp)
    sw $t0,4($sp)
    sw $t1,8($sp)
    lui $v0,0x8019
    ori $v0,$v0,0xb800
    lui $v1,0x8019
    ori $v1,$v1,0x7c00
    lui $t0,0x801e
    ori $t0,$t0,0x4400
1:
    lw $t1,0($v0)
    addiu $v0,$v0,4
    sw $t1,0($v1)
    bne $v0,$t0,1b
    addiu $v1,$v1,4
    lw $v0,0($sp)
    lw $t0,4($sp)
    lw $t1,8($sp)
    addiu $sp,$sp,16
    lui $v1,0x801a
    j 0x8003a9b4
    ori $v1,$v1,0xea1e

    .section .menu_loader,"ax",@progbits
    .globl kr_menu_read
kr_menu_read:
    # HARATA has already been expanded. Stage the compressed menu immediately
    # above its 384 KiB output; the later GPU packet pool overwrites this input.
    # The synchronous reader drains the CD queue before the native LZ decoder.
    addiu $sp,$sp,-24
    sw $ra,16($sp)
    jal 0x8003af2c
    lui $a1,0x801a
    lui $a0,0x801a
    jal 0x80037680
    lui $a1,0x8014
    lw $ra,16($sp)
    addiu $sp,$sp,24
    jr $ra
    nop

    .globl kr_menu_cached
kr_menu_cached:
    # Normal entry: HARATA and MENUMENU arrived in one contiguous CD read.
    # 0x80188000 + the sector-rounded 0x24800-byte overlay = 0x801ac800.
    lui $a0,0x801a
    ori $a0,$a0,0xc800
    j 0x80037680
    lui $a1,0x8014
