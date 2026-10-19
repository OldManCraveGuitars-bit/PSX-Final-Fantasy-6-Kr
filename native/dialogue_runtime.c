typedef unsigned char u8;
typedef unsigned short u16;
#define BUFFER ((u8 *)0x80033000)
#include "dialogue_huffman.h"

/* Restore one complete native byte stream before its first character is read.
   Pages, pauses, MTE tokens and two-byte operands remain byte-identical. */
u8 *kr_dialogue_expand(const u8 *p) {
    const u16 *h=kr_dialogue_huffman;
    const u8 *symbols=(const u8 *)(h+48);
    unsigned remaining=p[0]|(p[1]<<8),bits=0,nbit=0;
    u8 *out=BUFFER;
    p+=2;
    if(remaining>1024){BUFFER[0]=0;return BUFFER;}
    while(remaining--) {
        unsigned code=0,length=0;
        do {
            if(!nbit){bits=*p++;nbit=8;}
            code=(code<<1)|((bits>>7)&1);bits<<=1;nbit--;length++;
            if(length>=16){BUFFER[0]=0;return BUFFER;}
        }while(code<h[16+length] || code>=h[16+length]+h[length]);
        *out++=symbols[h[32+length]+code-h[16+length]];
    }
    return BUFFER;
}
