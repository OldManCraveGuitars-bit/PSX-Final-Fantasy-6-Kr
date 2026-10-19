#include "hangul_name.h"
#include "field_name_data.h"
typedef unsigned int u32;

unsigned kr_field_name(unsigned slot) {
    u8 *output=(u8 *)0x80027183;
    const u8 *name=(const u8 *)(0x8002f602+slot*37);
    unsigned i,j,index=slot*6,custom=slot<16,count=0,actor,unknown=1;
    const u8 *cache=(const u8 *)0x80030700;
    if (slot>=16) { *output=0;return 0; }
    while (count<6 && name[count]!=0xff) count++;
    if (*(const u32 *)cache!=0x314e524bU) cache=(const u8 *)0x80036000;
    if (*(const u32 *)cache!=0x314e524bU) custom=0;
    for (i=0;i<6;i++) {
        if(name[i]!=0xcb)unknown=0;
        if (name[i]!=0xff && name[i]!=0x60+index+i) custom=0;
    }
    if(unknown) {
        for(i=0;i<6;i++) {*output++=KR_NAME_QUESTION_0;*output++=KR_NAME_QUESTION_1;}
    } else if (custom) {
        const u16 *unicode=(const u16 *)(cache+16)+index;
        for (i=0;i<6 && name[i]!=0xff && unicode[i];i++) {
            if (unicode[i]==32) { *output++=0xff;continue; }
            const u8 *source=cache+208+(index+i)*30;
            u8 *glyph=(u8 *)0x80194bd0+(1152+index+i)*22;
            for (j=0;j<22;j++) glyph[j]=source[j];
            *(u8 *)(0x801946d0+32+1152+index+i)=12;
            *output++=0x1f;*output++=(u8)(0xa0+index+i);
        }
    } else {
        actor=*(const u8 *)(0x8002f600+slot*37);
        if (actor<64) {
            const u8 *source=kr_translated_names+kr_name_offsets[actor];
            while (*source) {
                unsigned c=*source++;*output++=(u8)c;
                if (c>=0x1c && c<=0x1f) *output++=*source++;
            }
        } else for (i=0;i<6 && name[i]!=0xff;i++) { *output++=0x1f;*output++=name[i]; }
    }
    *output=0;
    return ((slot*37+count)<<8)|(unsigned)(output-(u8 *)0x80027183);
}
