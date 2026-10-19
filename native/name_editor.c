#include "hangul_name.h"
#ifdef FF6_FIELD_CACHE
#pragma GCC optimize ("Os")
#endif
typedef unsigned int u32;
#define BYTE(a) (*(volatile u8 *)(a))
#define CACHE_MAGIC 0x314e524bU
#define CACHE ((NameCache *)0x80036000)
#define SAVE_MIRROR ((NameCache *)0x80030700)
#define EDITOR ((NameEditor *)0x80193000)
#ifdef FF6_FIELD_CACHE
#define SCRATCH ((u8 *)0x801a8000)
#define JAMO_FONTS ((const u8 *)0x8013c900)
#else
#define SCRATCH ((u8 *)0x80190000)
#define JAMO_FONTS ((const u8 *)0x8018f600)
#endif
#define NAME_FONTS ((const u8 *)0x80172000)
#define ASCII_FONTS ((const u8 *)0x80192000)
#define DEFAULT_NAMES ((const u16 *)0x80165400)
#define GRID_KEYS ((const u16 *)0x80165800)

typedef struct {
    u32 magic;
    u16 version,checksum;
    u8 reserved[8];
    u16 names[96];
    u8 glyphs[96][30];
} NameCache;
typedef struct {
    HangulName input;
    u16 last_block;
    u8 slot,active;
} NameEditor;
typedef struct { short x,y,w,h; } Rect;

static const u16 jamo[51] = {
    0x3131,0x3132,0x3134,0x3137,0x3138,0x3139,0x3141,0x3142,0x3143,0x3145,
    0x3146,0x3147,0x3148,0x3149,0x314a,0x314b,0x314c,0x314d,0x314e,
    0x314f,0x3150,0x3151,0x3152,0x3153,0x3154,0x3155,0x3156,0x3157,0x3158,
    0x3159,0x315a,0x315b,0x315c,0x315d,0x315e,0x315f,0x3160,0x3161,0x3162,0x3163,
    0x3133,0x3135,0x3136,0x313a,0x313b,0x313c,0x313d,0x313e,0x313f,0x3140,0x3144
};
static unsigned read16(const u8 *p) { return p[0]|(p[1]<<8); }
static unsigned read32(const u8 *p) { return read16(p)|(read16(p+2)<<16); }
static void copy(u8 *to,const u8 *from,unsigned n) {
    while (n--) *to++=*from++;
}
static void clear(u8 *to,unsigned n) { while (n--) *to++=0; }
static unsigned checksum_of(const NameCache *cache) {
    unsigned n=0,i;
    const u8 *p=(const u8 *)cache+16;
    for (i=0;i<sizeof(NameCache)-16;i++) n=(((n<<1)|(n>>15))^p[i])&0xffff;
    return n&0xffff;
}
static int valid_cache(const NameCache *cache) {
    if (cache->magic!=CACHE_MAGIC) return 0;
    if (cache->version==1 && cache->checksum==0xffff) return 1; /* Earlier development candidates. */
    return cache->version==2 && cache->checksum==checksum_of(cache);
}
static void decompress(const u8 *source,u8 *output) {
    unsigned size=read32(source),pos=0,flags,bit,token,distance,count;
    source+=4;
    if (size>7680) return;
    while (pos<size) {
        flags=read16(source);source+=2;
        for (bit=0;bit<8 && pos<size;bit++) {
            token=read16(source);source+=2;
            if (flags&(1<<bit)) {
                output[pos++]=(u8)token;output[pos++]=(u8)(token>>8);
            } else {
                distance=(token>>5)*2;count=((token&31)+2)*2;
                if (!distance || pos+count>size) return;
                while (count--) {
                    output[pos]=pos<distance?0:output[pos-distance];pos++;
                }
            }
        }
    }
}
static const u8 *record(unsigned c) {
    unsigned i,block,index;
#ifdef FF6_FIELD_CACHE
    if(!EDITOR->active && c>=0xac00 && c<=0xd7a3) {
        const u8 *dict=(const u8 *)0x8013c000;
        unsigned count=read32(dict);dict+=4;
        for(i=0;i<count;i++,dict+=32)if(read16(dict)==c)return dict+2;
        return ASCII_FONTS;
    }
#endif
    if (c>=0xac00 && c<=0xd7a3) {
        index=c-0xac00;block=index>>8;
        if (EDITOR->last_block!=block) {
            decompress(NAME_FONTS+read32(NAME_FONTS+24+block*8),SCRATCH);
            EDITOR->last_block=(u16)block;
        }
        return SCRATCH+(index&255)*30;
    }
    for (i=0;i<51;i++) if (jamo[i]==c) return JAMO_FONTS+i*30;
    if (c>=32 && c<127) return ASCII_FONTS+(c-32)*30;
    return ASCII_FONTS; /* Empty and space both have blank bitmaps. */
}
static void upload(unsigned tile,const u8 *bitmap) {
    u16 pixels[16];
    u8 planar[16];
    unsigned y,x,fg,shadow,nibble;
    Rect rect;
    int (*load_image)(const Rect *,const void *)=(void *)0x8005adb8;
    int (*draw_sync)(int)=(void *)0x8005ab0c;
    void (*convert_font)(const void *,unsigned,unsigned)=(void *)0x8003c9c8;
    for (y=0;y<8;y++) {
        pixels[y*2]=pixels[y*2+1]=0;
        fg=bitmap[y];
        shadow=(fg>>1)|(y?bitmap[y-1]:0)|(y?(bitmap[y-1]>>1):0);
        planar[y*2]=(u8)(fg|shadow);planar[y*2+1]=(u8)fg;
        for (x=0;x<8;x++) {
            nibble=(fg&(0x80>>x))?3:(shadow&(0x80>>x))?1:0;
            pixels[y*2+(x>>2)]|=(u16)(nibble<<((x&3)*4));
        }
    }
    /* Names also pass through the game's CPU-side glyph cache. */
    copy((u8 *)(0x8014a400+tile*16),planar,16);
    convert_font(planar,0x6000+tile*8,16);
    copy((u8 *)(0x800b5be8+tile*32),(const u8 *)pixels,32);
    rect.x=(short)(512+(tile&15)*2);rect.y=(short)((tile&0xf0)>>1);rect.w=2;rect.h=8;
    load_image(&rect,pixels);
    rect.x+=256;rect.y+=256;
    load_image(&rect,pixels);
    draw_sync(0);
}
static unsigned property(unsigned slot) { return 0x8002f600+slot*37; }
static int unknown_name(unsigned slot) {
    unsigned i;const u8 *name=(const u8 *)(property(slot)+2);
    for(i=0;i<6;i++)if(name[i]!=0xcb)return 0;
    return 1;
}
static int placeholders(unsigned slot) {
    unsigned i;const u8 *name=(const u8 *)(property(slot)+2);
    for (i=0;i<6;i++) if (name[i]!=0xff && name[i]!=0x60+slot*6+i) return 0;
    return 1;
}
static void store_name(unsigned slot,const u16 *text,unsigned length) {
    unsigned i,index=slot*6;
    u8 *name=(u8 *)(property(slot)+2);
    for (i=0;i<6;i++) {
        unsigned c=i<length?text[i]:0;
        CACHE->names[index+i]=(u16)c;
        copy(CACHE->glyphs[index+i],record(c),30);
        name[i]=c?(u8)(0x60+index+i):0xff;
    }
}
void kr_names_menu_init(void) {
    unsigned slot,i,actor,length;int valid;
    EDITOR->last_block=0xffff;EDITOR->active=0;
    if (valid_cache(SAVE_MIRROR))
        copy((u8 *)CACHE,(const u8 *)SAVE_MIRROR,sizeof(NameCache));
    else for (i=0;i<8;i++) CACHE->reserved[i]=0;
    valid=valid_cache(CACHE);
    if (!valid) clear((u8 *)CACHE,sizeof(NameCache));
    for (slot=0;slot<16;slot++) {
        actor=BYTE(property(slot));
        /* Preserve the story's unnamed marker. Empty actor slots have no
           visible names and need neither font decompression nor uploads. */
        if(actor>=64 || unknown_name(slot))continue;
        if (!valid || !placeholders(slot)) {
            const u16 *text=DEFAULT_NAMES+actor*6;
            for (length=0;length<6 && text[length];length++);
            store_name(slot,text,length);
        }
        for (i=0;i<6;i++) upload(0x60+slot*6+i,CACHE->glyphs[slot*6+i]+22);
    }
    CACHE->version=2;CACHE->checksum=(u16)checksum_of(CACHE);CACHE->magic=CACHE_MAGIC;
    copy((u8 *)SAVE_MIRROR,(const u8 *)CACHE,sizeof(NameCache));
}
static void preview(void) {
    u16 text[7];unsigned i,length=hn_text(&EDITOR->input,text);
    u8 *name=(u8 *)(property(EDITOR->slot)+2);
    for (i=0;i<6;i++) {
        upload(0x88+i,record(i<length?text[i]:0)+22);
        name[i]=i<length?(u8)(0x88+i):0xff;
        /* The native cache compares tile IDs. Composition changes the bitmap
           while keeping the same ID, so invalidate the six preview cells. */
        BYTE(0x80022129+i*2)=0xff;BYTE(0x8002212a+i*2)=0xff;
    }
    BYTE(0x8002e028)=EDITOR->input.count<6?EDITOR->input.count:5;
}
/* Share the separate menu helper block; the main code block borders labels. */
__attribute__((section(".bigtext"))) void kr_name_begin(void) {
    unsigned selected=read16((const u8 *)0x8002e067),i;
    unsigned slot=selected>=0xf600?(selected-0xf600)/37:0;
    void (*enable_interrupts)(void)=(void *)0x800d83f8;
#ifdef FF6_FIELD_CACHE
    ((void (*)(void))0x80135018)();
#endif
    if (slot>15) slot=0;
    EDITOR->slot=(u8)slot;EDITOR->active=1;
    hn_init(&EDITOR->input,6);
    {
        const u16 *name=CACHE->names+slot*6;
        if(unknown_name(slot) && BYTE(property(slot))<64)name=DEFAULT_NAMES+BYTE(property(slot))*6;
        for(i=0;i<6 && name[i];i++)hn_feed(&EDITOR->input,name[i]);
    }
    for (i=0;i<40;i++) upload(0x60+i,JAMO_FONTS+i*30+22);
    for (i=0;i<26;i++) upload(0xc0+i,record('A'+i)+22);
    { static const u8 punctuation[5]={'.','-','_','!','?'};
      for (i=0;i<5;i++) upload(0xda+i,record(punctuation[i])+22); }
    preview();enable_interrupts();
}
unsigned kr_name_keys(void) {
    unsigned low=BYTE(0x8002e008),high=BYTE(0x8002e009),length,index;
    u16 text[7];
    void (*select_sfx)(void)=(void *)0x800fca90;
    void (*erase_sfx)(void)=(void *)0x800fcb44;
    void (*invalid_sfx)(void)=(void *)0x800fcb08;
    if (!EDITOR->active) return 0;
    if (high&0x10) {
        length=hn_confirm(&EDITOR->input,text);
        if (!length) { invalid_sfx();return 0; }
        store_name(EDITOR->slot,text,length);
        CACHE->checksum=(u16)checksum_of(CACHE);
        copy((u8 *)SAVE_MIRROR,(const u8 *)CACHE,sizeof(NameCache));
        EDITOR->active=0;
        for (index=0;index<96;index++) upload(0x60+index,CACHE->glyphs[index]+22);
        return 1;
    }
    if (low&0x80) {
        index=BYTE(0x8002e04b)+BYTE(0x8002e04a);
        if (index<200 && hn_feed(&EDITOR->input,GRID_KEYS[index])) select_sfx();
        else invalid_sfx();
        preview();
    } else if (high&0x80) {
        hn_backspace(&EDITOR->input);erase_sfx();preview();
    } else if (high&0x40) {
        if (hn_feed(&EDITOR->input,0x20)) select_sfx();else invalid_sfx();
        preview();
    }
    return 0;
}
