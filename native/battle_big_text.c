typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;
#define BYTE(a) (*(volatile u8 *)(a))
#define CFG ((const u32 *)0x8019b7b0)
#define FONT 0x801d68f8
#define BUFFER ((u8 *)0x801e0680)
#define HUFF ((const u16 *)0x801e0500)
static unsigned read16(unsigned a) {return BYTE(a)|(BYTE(a+1)<<8);}
static void write16(unsigned a,unsigned n) {BYTE(a)=n;BYTE(a+1)=n>>8;}
static unsigned argument(void) {return **(volatile u16 **)0x8006c168;}
static unsigned text_pointer(void) {return 0x80000000|read16(0x8002e048)|(BYTE(0x8002e04a)<<16);}
static void set_pointer(unsigned p) {write16(0x8002e048,p);BYTE(0x8002e04a)=p>>16;}

/* Canonical Huffman streams retain every native control byte and operand. */
void kr_big_expand(unsigned id,u8 *out) {
    const u8 *p=(const u8 *)(0x801ad200+((unsigned)((const u16 *)CFG[0])[id]<<1));
    const u8 *symbols=(const u8 *)(HUFF+48);
    unsigned remaining=*p++,bits=0,nbit=0;
    while(remaining--) {
        unsigned code=0,length=0;
        do {
            if(!nbit) {bits=*p++;nbit=8;}
            code=(code<<1)|((bits>>7)&1);bits<<=1;nbit--;length++;
        } while(code<HUFF[16+length] || code>=HUFF[16+length]+HUFF[length]);
        *out++=symbols[HUFF[32+length]+code-HUFF[16+length]];
    }
}
void kr_big_reference(void) {
    const u8 *p=(const u8 *)text_pointer();
    unsigned id=p[1]-1+(p[2]-1)*255;
    kr_big_expand(id,BUFFER);set_pointer((unsigned)BUFFER-1);
}
extern void kr_big_original_glyph(void);
void kr_big_glyph(void) {
    unsigned x=BYTE(0x8002e07a),index=read16(0x8002e026)/22;
    /* Native full-width digits lived inside the font tail now occupied by
       this runtime/LUT. Both encoded names and native numeric controls use
       those indices, so redirect at the shared rasterizer entry. */
    if(index>=1075 && index<1085)write16(0x8002e026,(901+index-1075)*22);
    kr_big_original_glyph();
    BYTE(0x8002e07a)=x+(index==223?6:12);
}
static void glyph(unsigned index) {write16(0x8002e026,index*22);kr_big_glyph();}
static void large_word(unsigned id) {
    u8 text[256];const u8 *p=text;kr_big_expand(id,text);
    while(*p) {
        unsigned c=*p++,index;
        if(c>=0x1c && c<=0x1f)index=224+((c-0x1c)<<8)+*p++;
        else if(c>=32)index=c-32;
        else continue;
        glyph(index);
    }
}
static void small_word(unsigned id) {
    const u8 *p=*(const u8 **)(0x80198b00+id*4);
    if(*p==0x16)p++;
    while(*p && *p!=0xff) {
        unsigned c=*p++,tile,index;
        if(c==32) {glyph(223);continue;}
        if(c>=2 && c<=0x1a)continue; /* Item type icons have no large counterpart. */
        if(c>=0x1c && c<=0x1f)tile=((c-0x1c)<<8)|*p++;
        else if(c==0x1b)tile=256+*p++;
        else if(c>=0x80)tile=read16(0x8019b600+(c-0x80)*2);
        else tile=256+BYTE(0x8019b700+c);
        index=read16(0x8019ae00+tile*2);
        if(index!=0xffff)glyph(index);
    }
}
void kr_big_attack(void) {unsigned id=argument()&255;if(id<54)small_word(64+id);else if(id<255)large_word(id-54);}
void kr_big_item(void) {small_word(150+(argument()&255));}
void kr_big_command(void) {unsigned id=argument()&255;if(id<32)small_word(118+id);}
static void character_name(unsigned actor,unsigned name) {
    unsigned i;
    if(name) {
        unsigned first=BYTE(name),custom=first>=0x60 && first<0xc0 && (first-0x60)%6==0,unknown=1;
        for(i=0;i<6;i++) {
            unsigned c=BYTE(name+i);
            if(c!=0xff && c!=first+i)custom=0;
            if(c!=0xcb)unknown=0;
        }
        if(unknown) {for(i=0;i<6;i++)glyph(CFG[2]);return;}
        if(custom && *(const u32 *)0x80036000==0x314e524b) {
            for(i=0;i<6 && BYTE(name+i)!=0xff;i++) {
                unsigned k=first-0x60+i,c=read16(0x80036000+16+k*2),j;
                if(!c)break;
                if(c==32)glyph(223);
                else {
                    for(j=0;j<22;j++)BYTE(FONT+930*22+j)=BYTE(0x80036000+208+k*30+j);
                    glyph(930);
                }
            }
            return;
        }
    }
    small_word(actor&63);
}
void kr_big_character(void) {
    unsigned p=text_pointer()+1,actor=BYTE(p),slot;set_pointer(p);
    for(slot=0;slot<16;slot++)if(BYTE(0x8002f600+slot*37)==actor)break;
    character_name(actor,slot<16?0x8002f602+slot*37:0);
}
/* Victory {string[00]} uses a battle-party slot, not a script actor ID.
 * Its original six-byte glyph loop bypassed every translated-name hook. */
void kr_big_reward_character(void) {
    unsigned slot=BYTE(0x80020f38),address,actor,i,j;
    if(slot>=4)return;
    address=0x80020000+read16(0x8018a920+slot*2);
    actor=BYTE(address)&63;
    for(i=0;i<16;i++) {
        unsigned p=0x8002f600+i*37,match=BYTE(p)!=0xff;
        for(j=0;j<6;j++)if(BYTE(p+2+j)!=BYTE(address+1+j))match=0;
        if(match){actor=BYTE(p);break;}
    }
    character_name(actor,address+1);
}
static void big_small(unsigned offset,unsigned width,unsigned list) {
    u8 text[256];const u8 *p=text;
    volatile u16 *native_y=*(volatile u16 **)0x8006c1a0;
    unsigned y=*native_y,count=0,upper,lower,palette;
    kr_big_expand(offset/8,text);
    if(list){upper=read16(0x8002e051);lower=read16(0x8002e053);palette=BYTE(0x8002e056);}
    else {upper=read16(0x8002e04a);lower=read16(0x8002e04c);palette=BYTE(0x8002e04e);}
    while(count++<width) {
        unsigned c=*p,tile=0x21ff,index;
        if(c) {
            p++;
            if(c==0xff)tile=0x8ffe;
            else {
                if(c>=0x1c && c<=0x1f)index=224+((c-0x1c)<<8)+*p++;
                else index=c-32;
                tile=((const u16 *)CFG[1])[index];
                if(tile==0xffff)tile=0x21ff;
                else {
                    if(tile>=512 || (tile>=352 && tile<448))tile|=0x8000;
                    tile|=(palette&0xfc)<<8;
                }
            }
        }
        write16(0x80020000+upper+y,0x21ff);write16(0x80020000+lower+y,tile);y+=2;
    }
    *native_y=y;
}
void kr_big_small_list(unsigned offset) {big_small(offset,8,1);}
void kr_big_small_menu(unsigned offset) {big_small(offset,8,0);}
void kr_big_small_magitek(unsigned offset) {big_small(offset+85*8,8,1);}
void kr_big_small_bushido(unsigned offset) {big_small(offset+77*8,8,1);}
unsigned kr_big_monster_attack_source(unsigned offset) {
    /* A reference operand may be FF (e.g. Silvario's record 254). The native
       eight-byte name copier treats FF as an end marker, so write the whole
       reference directly to its destination instead of that copier. */
    unsigned id=229+offset/8;u8 *p=(u8 *)0x800237d5;
    p[0]=0x18;p[1]=id%255+1;p[2]=id/255+1;p[3]=0;
    return (unsigned)p;
}
void kr_big_esper_attack_copy(unsigned offset) {
    unsigned id=202+offset/9;
    BYTE(0x800237d5)=0x18;BYTE(0x800237d6)=id%255+1;BYTE(0x800237d7)=id/255+1;BYTE(0x800237d8)=0;
}
