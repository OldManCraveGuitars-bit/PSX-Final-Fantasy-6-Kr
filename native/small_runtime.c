#include "hangul_name.h"

#define BYTE(a) (*(volatile u8 *)(a))
typedef unsigned int u32;
typedef struct { short x,y,w,h; } Rect;
void kr_names_menu_init(void);

static unsigned read16(unsigned address) {
    return BYTE(address)|(BYTE(address+1)<<8);
}
static void write16(unsigned address,unsigned value) {
    BYTE(address)=(u8)value; BYTE(address+1)=(u8)(value>>8);
}
static void canvas_position(unsigned address,Rect *rect,unsigned shift) {
    unsigned offset=address-0x80021849;
    rect->x=(short)(0x100+((offset&63)<<1)+(offset>0x800?0x80:0)-shift/2);
    rect->y=(short)(0x100+((offset>>3)&0xf8));rect->w=4;rect->h=8;
}
static void canvas_clear(unsigned address) {
    Rect rect;
    int (*clear_image)(const Rect *,int,int,int)=(void *)0x8005ac90;
    canvas_position(address,&rect,0);clear_image(&rect,0,0,0);
}
static void canvas_glyph(unsigned address,unsigned tile,unsigned palette,unsigned shift) {
    Rect rect;unsigned y,x,u=(tile&15)*8+((tile&512)>>2),v=(tile&0x1f0)>>1;
    const u8 *atlas=(const u8 *)0x80166000;
    u8 *temporary_font=(u8 *)(0x800b5be8+255*32);
    u8 saved[32];
    void (*blit)(unsigned,unsigned,unsigned,unsigned)=(void *)0x801258c4;
    for (x=0;x<32;x++) saved[x]=temporary_font[x];
    for (y=0;y<8;y++) for (x=0;x<4;x++) temporary_font[y*4+x]=atlas[(v+y)*128+u/2+x];
    canvas_position(address,&rect,shift);blit(0x5000,palette|255,(unsigned short)rect.x,(unsigned short)rect.y);
    for (x=0;x<32;x++) temporary_font[x]=saved[x];
}
void kr_boost_line(unsigned x,unsigned y,unsigned palette,const u16 *text) {
    unsigned address=0x80021849+y*64+x*2,shift=0,tile;
    while((tile=*text++)!=0xffff) {
        if(tile==0x8ffe)shift+=4;
        else canvas_glyph(address,tile,palette,shift);
        write16(address,tile==0x8ffe?tile:tile|palette);address+=2;
    }
    write16(address,0xcfff);
}
void kr_boost_header(const u16 *text) {
    unsigned address=0x8002588f,tile;
    while((tile=*text++)!=0xffff) {
        write16(address,tile==0x8ffe?tile:tile|0xa000);address+=2;
    }
    write16(address,0xcfff);
}
void kr_upload_small(void) {
    Rect rect={512,0,64,256};
    int (*load_image)(const Rect *,const void *)=(void *)0x8005adb8;
    int (*draw_sync)(int)=(void *)0x8005ab0c;
    load_image(&rect,(const void *)0x80166000);
    /* The menu uses a second texture page for BG2. */
    rect.x=768; rect.y=256;
    load_image(&rect,(const void *)0x80166000);
    draw_sync(0);
    kr_names_menu_init();
}

void kr_restore_small_after_save(void) {
    void (*finish_menu_graphics)(void)=(void *)0x8011f93c;
    int (*load_image)(const Rect *,const void *)=(void *)0x8005adb8;
    int (*draw_sync)(int)=(void *)0x8005ab0c;
    Rect rect={512,0,64,256};
    /* The native save-return task (8010e1ec) rebuilds all original font pages.
       Run its final canvas setup, then restore only the extended sprite page.
       This task finishes after the earlier menu graphics initializer. */
    finish_menu_graphics();
    draw_sync(0);
    load_image(&rect,(const void *)0x80166000);
    draw_sync(0);
}

/* Tagged label records: native XY, 1b, little-endian tile IDs, ff. */
static void copy_label(unsigned lower_row) {
    unsigned source=0x80000000|read16(0x8002e0e7)|(BYTE(0x8002e0e9)<<16);
    unsigned original_source=source,tag=BYTE(source+2),shift=0,word_offset=3;
    if (tag>=0xe0 && BYTE(source+3)==0x17) { tag=0x17;word_offset=4; }
    if (tag==0x15 || tag==0x14) {
        unsigned id=tag==0x15?BYTE(source+3):read16(source+3);
        source=0x80170000+read16(0x80195800+id*2);tag=BYTE(source+2);
    }
    unsigned xy=read16(source), offset=read16(0x8002e000);
    unsigned destination=0x80020000+((xy+offset+lower_row)&0xffff);
    unsigned palette=BYTE(0x8002e029)<<8;
    unsigned count=0;
    const u8 *stream=(const u8 *)(source+3);
    if (tag==0x17) {
        unsigned id=read16(source+word_offset),i;
        /* Job titles share a seven-cell canvas when cycling party members.
           Clear the complete old title, including its half-space tail. */
        if (id>=711 && id<775) for(i=0;i<7;i++) {
            unsigned at=destination+i*2;
            if (at>=0x80021849 && at<0x80023849) {
                canvas_clear(at);
                if(lower_row)canvas_clear(at-lower_row);
            }
            write16(at,0);
            if(lower_row)write16(at-lower_row,0);
        }
        stream=*(const u8 **)(0x80193020+id*4);
        tag=*stream++;
    }
    if (tag==0x18) {
        unsigned id=(stream[0]-1)+(stream[1]-1)*255;
        stream=*(const u8 **)(0x80196000+id*4);
        tag=*stream++;
    }
    unsigned tile;
    while (count<64) {
        if (tag==0x16) {
            unsigned c=*stream++;
            if (!c || c==0xff) break;
            if (c==32) tile=0x8ffe;
            else if (c>=2 && c<=0x1a) tile=BYTE(0x80170d80+c-2);
            else if (c>=0x1c && c<=0x1f) tile=((c-0x1c)<<8)|*stream++;
            else if (c==0x1b) tile=*stream++;
            else if (c>=0x80) tile=read16(0x80170e00+(c-0x80)*2);
            else tile=BYTE(0x80170d00+c);
        } else {
            if (stream[0]==0xff) break;
            tile=stream[0]|(stream[1]<<8);stream+=2;
        }
        if (destination>=0x80021849 && destination<0x80023849) {
            if (lower_row) canvas_clear(destination-lower_row);
            if (tile==0x8ffe) shift+=4;
            else canvas_glyph(destination,tile,palette,shift);
        }
        if (tile!=0x8ffe && tile!=0xcfff) {
            tile|=palette;
            /* Native BG2 canvas tiles share the same numbers as extended
               glyphs. Mark only translated sprite text for texture routing. */
            if (!(destination>=0x80021849 && destination<0x80023849)) tile|=0x8000;
        }
        if (lower_row) write16(destination-lower_row,0);
        write16(destination,tile); destination+=2;count++;
    }
    write16(destination,0xcfff);
    /* Match the original routine's source and destination bookkeeping. */
    write16(0x8002e0eb,xy);
    write16(0x8002e0e7,original_source+2);
    BYTE(0x8002e0e9)=(u8)((original_source+2)>>16);
    BYTE(0x8002e0ed)=2;
}
void kr_copy_label(void) { copy_label(0); }
void kr_copy_rich_label(void) { copy_label(0x40); }
