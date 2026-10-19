typedef unsigned char u8;
typedef unsigned int u32;
#define MAGIC 0x3143464bU
#define HEADER ((volatile u32 *)0x801e2000)
static void (*copy)(void *,const void *,unsigned)=(void *)0x800543ac;
/* Single-probe LZ4 encoder with a hard output limit; failure is harmless.
   Hash workspace never overlaps either input or output. */
unsigned kr_cache_pack(const u8 *src,unsigned size,u8 *dst,unsigned cap,u32 *table) {
    const u8 *p=src,*anchor=src,*end=src+size,*match,*start;
    u8 *out=dst,*limit=dst+cap,*token;unsigned i,n,l,off,h;
    for(i=0;i<8192;i++)table[i]=0;
    *(u32 *)out=size;out+=4;
    while(p+12<end) {
        u32 word=(u32)p[0]|((u32)p[1]<<8)|((u32)p[2]<<16)|((u32)p[3]<<24);
        h=(word*2654435761U)>>19;match=(const u8 *)table[h];table[h]=(u32)p;
        if(!match || p-match>65535 || match[0]!=p[0] || match[1]!=p[1] || match[2]!=p[2] || match[3]!=p[3]) { p++;continue; }
        l=(unsigned)(p-anchor);off=(unsigned)(p-match);start=p;p+=4;match+=4;
        while(p<end-5 && *p==*match){p++;match++;}
        n=(unsigned)(p-start)-4;
        if(out+1+l+l/255+3+n/255+2>limit)return 0;
        token=out++;*token=(u8)((l<15?l:15)<<4)|(u8)(n<15?n:15);
        if(l>=15){i=l-15;while(i>=255){*out++=255;i-=255;}*out++=(u8)i;}
        while(anchor<start)*out++=*anchor++;
        *out++=(u8)off;*out++=(u8)(off>>8);
        if(n>=15){i=n-15;while(i>=255){*out++=255;i-=255;}*out++=(u8)i;}
        anchor=p;
    }
    l=(unsigned)(end-anchor);
    if(out+1+l+l/255+1>limit)return 0;
    *out++=(u8)((l<15?l:15)<<4);
    if(l>=15){i=l-15;while(i>=255){*out++=255;i-=255;}*out++=(u8)i;}
    while(anchor<end)*out++=*anchor++;
    return (unsigned)(out-dst);
}

void kr_cache_preserve(void) {
    unsigned tail=0,graphics=0,words,i;u32 *from,*to;
    {
        HEADER[0]=0;
        copy((void *)0x800c8000,(const void *)0x80188000,0x43800);
        tail=kr_cache_pack((const u8 *)0x800c8000,0x43800,(u8 *)0x801a8000,0x3a000,(u32 *)0x8010c000);
        if(tail) {
            words=(tail+3)>>2;from=(u32 *)0x801a8000+words;to=(u32 *)0x801e2000;
            for(i=0;i<words;i++)*--to=*--from;
            HEADER[1]=(u32)to;
            /* Same four vertical blocks as the native menu backup. */
            ((void (*)(unsigned,unsigned,void *,unsigned,unsigned,unsigned))0x8003ee34)
                (512,256,(void *)0x800c8000,0x20000,448,256);
            graphics=kr_cache_pack((const u8 *)0x800c8000,0x20000,(u8 *)0x80179000,0x19000,(u32 *)0x800e8000);
        }
        HEADER[2]=tail;HEADER[3]=graphics;
        HEADER[0]=(tail && graphics)?MAGIC:0;
    }
}
