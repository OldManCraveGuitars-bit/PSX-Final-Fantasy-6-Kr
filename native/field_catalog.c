typedef unsigned char u8;
typedef unsigned int u32;
#define CFG ((const u32 *)0x801a3cfc)
void kr_field_catalog(unsigned category) {
    unsigned id=*(const u8 *)(category?0x8002e584:0x8002e583),i;
    u8 *out=(u8 *)0x80027183;
    const u8 *source;
    if(category)id=256+(id<54?id:0);
    source=(const u8 *)CFG[1];
    for(i=0;i<CFG[2]*22;i++)((u8 *)0x8019aed0)[i]=source[i];
    for(i=0;i<CFG[2];i++)((u8 *)0x801946d0)[32+1152+i]=12;
    source=((const u8 * const *)CFG[0])[id];
    for(;;) {
        unsigned c=*source++;*out++=c;
        if(!c)break;
        if(c>=0x1c && c<=0x1f)*out++=*source++;
    }
}
