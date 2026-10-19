    .set noreorder
    .text
    .globl kr_field_menu_return
kr_field_menu_return:
    # Enter from the resident loader after its original stack prologue.
    # This replaces only the full-read path; partial field reloads stay native.
    # The subsequent map initialization reads NAR_BIN2. Its identical nearby
    # mirror avoids seeking back across the disc immediately after this bank.
    li $t0,FIELD_TEXTURE_NEAR_MSF
    lui $t1,0x8006
    sw $t0,0x3470($t1)
    la $a0,field_bin_msf
    lui $a1,0x800c
    ori $a1,$a1,0x8000
    move $a2,$zero
    li $a3,FIELD_BIN_PACKED_SIZE
    jal 0x8003af2c
    nop
    lui $a0,0x800c
    ori $a0,$a0,0x8000
    jal kr_menu_unpack
    lui $a1,0x8013

    la $a0,field_tail_msf
    lui $a1,0x800e
    ori $a1,$a1,0x8000
    move $a2,$zero
    li $a3,FIELD_TAIL_PACKED_SIZE
    # Let the original GPU initialization run while this CD read is pending.
    jal 0x8003afd8
    nop
    j 0x8003a5a4
    nop

    .globl kr_field_menu_after_wait
kr_field_menu_after_wait:
    # The native queue drain at 8003A5FC has completed. Modes 1/2 still use
    # their original partial read path and must not decode this packed bank.
    addiu $v0,$s0,-1
    sltiu $v0,$v0,2
    bnez $v0,partial
    nop
    lui $a0,0x800e
    ori $a0,$a0,0x8000
    lui $a1,0x800c
    ori $a1,$a1,0x8000
    jal kr_menu_unpack
    nop
    # Move the native PAC backward into its original input buffer, then run
    # the untouched native graphics upload/swap and native PAC decoder.
    j 0x8003a4b0
    nop
partial:
    # Battle/world partial returns continue to use the original nearby field
    # archives, so restore their original texture route as well.
    li $t0,FIELD_TEXTURE_ORIGINAL_MSF
    lui $t1,0x8006
    sw $t0,0x3470($t1)
    j 0x8003a610
    ori $a0,$zero,0x200
field_bin_msf:
    .word FIELD_BIN_MSF
field_tail_msf:
    .word FIELD_TAIL_MSF
