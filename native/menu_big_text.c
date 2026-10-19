/* Decode translated menu descriptions and the native large-name tables. */
typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;

__attribute__((section(".bigtext"))) void kr_big_expand(void) {
    volatile u8 *text=(volatile u8 *)0x80027ec9;
    if (text[0]==0x18) {
        unsigned id=(text[1]-1)+(text[2]-1)*255,n=0,code;
        const u8 *source=*(const u8 **)(0x80194000+id*4);
        do {
            code=source[n];text[n++]=(u8)code;
            if (code>=0x1c && code<=0x1f && n<255) { text[n]=source[n];n++; }
        } while (code && n<255);
    }
}

__attribute__((section(".bigtext"))) void kr_big_get_letter(void) {
    volatile u16 *a=*(volatile u16 **)0x8006c168;
    volatile u16 *x=*(volatile u16 **)0x8006c19c;
    volatile u8 *text=(volatile u8 *)0x80027ec9;
    unsigned position=*x,code=*a&255,base=0,index;
    if (text[0]==0x18) { kr_big_expand();code=text[position]; }
    if (code>=0x1c && code<=0x1f) {
        base=0x1340+(code-0x1c)*0x1600;
        code=text[++position];index=224+(base-0x1340)/22+code;
    } else { code=(code-0x20)&255;index=code; }
    *(volatile u16 *)0x8002e0eb=(u16)base;
    *(volatile u8 *)0x8002e0b6=*(const u8 *)(0x80152adb+index+32);
    *a=(u16)code;*x=(u16)position;
}
