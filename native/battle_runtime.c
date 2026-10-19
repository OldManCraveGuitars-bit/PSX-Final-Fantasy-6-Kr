typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;
#define BYTE(a) (*(volatile u8 *)(a))
typedef struct {short x,y,w,h;} Rect;
static unsigned read16(unsigned a) {return BYTE(a)|(BYTE(a+1)<<8);}
static void write16(unsigned a,unsigned v) { BYTE(a)=(u8)v;BYTE(a+1)=(u8)(v>>8); }

static void upload_tile(unsigned tile,const u8 *bitmap) {
    Rect rectangle={(short)(704+(tile&15)*2),(short)((tile&0x1f0)>>1),2,8};
    u16 pixels[16];unsigned y,x;
    for(y=0;y<8;y++) {
        unsigned fg=bitmap[y],shadow=(fg>>1)|(y?bitmap[y-1]:0)|(y?bitmap[y-1]>>1:0);
        pixels[y*2]=pixels[y*2+1]=0;
        for(x=0;x<8;x++)pixels[y*2+(x>>2)]|=(u16)(((fg&(0x80>>x))?3:(shadow&(0x80>>x))?1:0)<<((x&3)*4));
    }
    ((int (*)(const Rect *,const void *))0x8005adb8)(&rectangle,pixels);
    ((int (*)(int))0x8005ab0c)(0);
}

void kr_battle_upload(void) {
    if (*(volatile u32 *)0x8019b7a0!=0x3142544b) {
        /* Keep the native BG3 canvas at 640..704,256..512 intact. Magic's
           right-hand pane uses that canvas, including the former atlas area. */
        Rect rectangle={736,0,32,8};unsigned row,y,x;
        u8 font[4672];
        int (*load_image)(const Rect *,const void *)=(void *)0x8005adb8;
        int (*draw_sync)(int)=(void *)0x8005ab0c;
        unsigned (*decompress)(const void *,void *)=(void *)0x80041cec;
        decompress(*(const void * const *)0x8019b7a8,font);
        for (row=0;row<32;row++) {
            u16 pixels[256];
            for (y=0;y<8;y++) for (x=0;x<128;x+=4) {
                unsigned k,pixel=0;
                for (k=0;k<4;k++) {
                    unsigned column=x+k,bit=0x80>>(column&7);
                    const u8 *bitmap=font+(72+row*16+(column>>3))*8;
                    unsigned fg=bitmap[y],shadow=(fg>>1)|(y?bitmap[y-1]:0)|(y?bitmap[y-1]>>1:0);
                    pixel|=((fg&bit)?3:(shadow&bit)?1:0)<<(k*4);
                }
                pixels[y*32+(x>>2)]=(u16)pixel;
            }
            rectangle.y=(short)(row*8);load_image(&rectangle,pixels);draw_sync(0);
        }
        for(x=0;x<72;x++)upload_tile(376+x,font+x*8);
        if (*(const u32 *)0x80036000==0x314e524b) {
            unsigned party,i;
            for(party=0;party<4;party++) {
                unsigned name=0x80020eaf+party*32,first=BYTE(name),custom=first>=0x60 && first<0xc0 && (first-0x60)%6==0;
                for(i=0;i<6;i++)if(BYTE(name+i)!=0xff && BYTE(name+i)!=first+i)custom=0;
                if(custom) for(i=0;i<6;i++)
                    upload_tile(0x160+party*6+i,(const u8 *)(0x80036000+208+(first-0x60+i)*30+22));
            }
        }
        *(volatile u32 *)0x8019b7a0=0x3142544b;
    }
}

static void word(unsigned id,unsigned width,unsigned list) {
    const u8 *stream=*(const u8 **)(0x80198b00+id*4);
    volatile u16 *native_y=*(volatile u16 **)0x8006c1a0;
    unsigned y=*native_y,count=0,upper,lower,palette;
    if (list) {upper=read16(0x8002e051);lower=read16(0x8002e053);palette=BYTE(0x8002e056);}
    else {upper=read16(0x8002e04a);lower=read16(0x8002e04c);palette=BYTE(0x8002e04e);}
    if (*stream==0x16) stream++;
    while (count<width) {
        unsigned c=*stream,tile;
        if (!c || c==0xff) tile=0x21ff;
        else {
            stream++;
            if (c==32) tile=0x8ffe;
            else if (c>=2 && c<=0x1a) tile=256+BYTE(0x8019b780+c-2);
            else if (c>=0x1c && c<=0x1f) tile=((c-0x1c)<<8)|*stream++;
            else if (c==0x1b) tile=256+*stream++;
            else if (c>=0x80) tile=read16(0x8019b600+(c-0x80)*2);
            else tile=256+BYTE(0x8019b700+c);
            if (tile!=0x8ffe) {
                if (tile>=512 || (tile>=352 && tile<448)) tile|=0x8000;
                tile|=(palette&0xfc)<<8;
            }
        }
        write16(0x80020000+upper+y,0x21ff);
        write16(0x80020000+lower+y,tile);
        y+=2;count++;
    }
    *native_y=(u16)y;
}
void kr_battle_monster(unsigned offset) {word(406+offset/8,8,0);}
void kr_battle_command(unsigned offset) {word(118+offset/6,6,0);}
void kr_battle_spell_list(unsigned offset) {word(64+offset/5,9,1);}
void kr_battle_spell_short(unsigned offset) {word(64+offset/5,5,1);}
void kr_battle_spell_menu(unsigned offset) {word(64+offset/5,5,0);}
void kr_battle_item_list(unsigned offset) {word(150+offset/9,9,1);}
void kr_battle_item_menu(unsigned offset) {word(150+offset/9,9,0);}
void kr_battle_monster_list(unsigned offset) {word(406+offset/8,8,1);}

void kr_battle_character(void) {
    unsigned address=0x80020000+read16(0x8002e010),i,first=BYTE(address+1),custom=first>=0x60 && first<0xc0 && (first-0x60)%6==0;
    unsigned unknown=1;
    for (i=0;i<6;i++) {
        unsigned c=BYTE(address+1+i);
        if (c!=0xff && c!=first+i) custom=0;
        if (c!=0xcb) unknown=0;
    }
    if ((custom && *(const u32 *)0x80036000==0x314e524b) || unknown) {
        volatile u16 *native_y=*(volatile u16 **)0x8006c1a0;
        unsigned y=*native_y,upper=read16(0x8002e04a),lower=read16(0x8002e04c),palette=(BYTE(0x8002e04e)&0xfc)<<8;
        unsigned party=(address-0x80020eae)/32;
        if(party>3)party=0;
        for (i=0;i<6;i++) {
            unsigned c=unknown?'?':read16(0x80036000+16+(first-0x60+i)*2),tile;
            if (unknown) tile=0x1cb|palette;
            else if (!c) tile=0x21ff;
            else if (c==32) tile=0x8ffe;
            else tile=(0x160+party*6+i)|palette|0x8000;
            write16(0x80020000+upper+y,0x21ff);write16(0x80020000+lower+y,tile);y+=2;
        }
        *native_y=(u16)y;
    } else {
        unsigned actor=BYTE(address)&63,slot;
        for (slot=0;slot<16;slot++) {
            unsigned p=0x8002f600+slot*37,match=BYTE(p)!=0xff;
            for (i=0;i<6;i++) if (BYTE(p+2+i)!=BYTE(address+1+i)) match=0;
            if (match) {actor=BYTE(p)&63;break;}
        }
        word(actor,6,0);
    }
}
