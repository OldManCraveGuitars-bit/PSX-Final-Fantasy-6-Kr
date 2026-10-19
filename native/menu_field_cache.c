/* Experimental bounded field cache. All buffers are explicitly owned here. */
typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;
#include "menu-field-cache-routes.h"
#define MAGIC 0x3143464bU
#define HEADER ((volatile u32 *)0x801e2000)
#define RETURN __attribute__((section(".cache_return")))
typedef struct { short x,y,w,h; } Rect;
static void (*unpack)(const void *,void *)=(void *)0x80037680;
static void (*read_cd)(const void *,void *,unsigned,unsigned)=(void *)0x8003af2c;

void kr_cache_menu_load(void) {
    static const u32 msf1=MENU_PART1_MSF;
    read_cd(&msf1,(void *)MENU_PART1_SOURCE,0,MENU_PART1_BYTES+MENU_PART2_BYTES);
    unpack((const void *)MENU_PART1_SOURCE,(void *)0x80140000);
    unpack((const void *)MENU_PART2_SOURCE,(void *)0x80192000);
}
void kr_cache_name_load(void) {
    static const u32 msf=MENU_NAME_MSF;
    HEADER[0]=0;
    read_cd(&msf,(void *)0x80172000,0,MENU_NAME_BYTES);
}

/* Copied to 8012c000 only after the menu has completely finished.
   This survives the prefix and native field-overlay decompressions. */
RETURN void kr_cache_field_return(unsigned init) {
    u32 msf=FIELD_CACHE_MSF,gp;
    unsigned *last;
    ((void (*)(unsigned))0x80046d84)(0);
    ((void (*)(void))0x8004d398)();
    /* Disc DMA and cached graphics reconstruction use disjoint buffers. */
    ((void (*)(const void *,void *,unsigned,unsigned))0x8003afd8)(&msf,(void *)0x800c8000,0,FIELD_CACHE_READ_BYTES);
    HEADER[0]=0;
    ((void (*)(const void *,void *))0x80037680)((const void *)0x80179000,(void *)0x80140000);
    ((void (*)(unsigned,unsigned,const void *,unsigned))0x8003ef20)(512,256,(const void *)0x80140000,0x20000);
    if(init==2)((void (*)(void))0x80040734)();
    ((void (*)(const void *,void *))0x80037680)((const void *)HEADER[1],(void *)0x80188000);
    ((void (*)(void))0x8004d398)();
    ((void (*)(const void *,void *))0x80037680)((const void *)0x800c8000,(void *)0x80130000);
    ((void (*)(const void *,void *))0x80041cec)((const void *)FIELD_CACHE_PAC_SOURCE,(void *)0x800c8000);
    *(volatile u32 *)0x80063470=FIELD_NEAR_TEXTURE_MSF;
    __asm__ volatile("move %0,$gp":"=r"(gp));
    last=(unsigned *)gp;
    last[0x210/4]=last[0x20c/4]=last[0x208/4]=last[0x1d8/4]=last[0x218/4]=last[0x1f4/4]=~0U;
}
