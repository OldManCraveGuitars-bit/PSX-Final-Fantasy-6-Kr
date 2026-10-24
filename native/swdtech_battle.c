typedef unsigned char u8;
typedef unsigned short u16;
/* Dedicated free font-tail slots, beyond the unchanged v086 renderer/LUT. */
#define LETTERS ((const u16 *)0x801dd200)
unsigned kr_swdtech_battle(unsigned offset) {
    const u8 *name=(const u8 *)(0x8002fcf8+offset);
    u8 *out=(u8 *)0x800237d5;unsigned i;
    if(offset>=48 || offset%6)return 0;
    for(i=0;i<6;i++) {
        unsigned value;
        if(name[i]==255)continue;
        value=LETTERS[name[i]];
        *out++=value;
        if(value>>8)*out++=value>>8;
    }
    *out=0;return 1;
}
