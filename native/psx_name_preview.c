/* The existing 8 KiB file buffer gains 4 KiB of private font storage.
 * Textures occupy only the verified empty rectangle below the PSX UI font.
 * The field/battle name cache and all original portrait/icon pages stay intact.
 */
typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;
#include "psx-name-data.h"
#define LAST ((u8 *)0x800dded8)
#define PENDING (*(u32 *)0x800ddf08)
#define LAST_RANK (*(u32 *)0x800ddf0c)
#define OUTPUT ((u8 *)0x800e9c5c)
#define DEFAULTS ((const u16 *)0x800c8c58)
#define GLYPHS ((const u8 *)PSX_NAME_FONT_ADDRESS)
typedef struct {short x,y,w,h;} Rect;
static unsigned r16(const u8 *p) {return p[0]|(p[1]<<8);}
static void copy(u8 *d,const u8 *s,unsigned n) {while(n--)*d++=*s++;}
static u8 *buffer(void) {return *(u8 **)(*(u32 *)0x800eeec0+0xb8);}
static int cache_valid(const u8 *c) {
    unsigned i,sum=0;
    if(*(const u32 *)c!=0x314e524b)return 0;
    if(r16(c+4)==1 && r16(c+6)==65535)return 1;
    for(i=16;i<3088;i++)sum=(((sum<<1)|(sum>>15))^c[i])&65535;
    return r16(c+4)==2 && r16(c+6)==sum;
}
static void upload(unsigned tile,const u8 *bits) {
    Rect rect={(short)(512+(tile&31)*2),(short)(416+(tile>>5)*8),2,8};
    u16 pixels[16];unsigned x,y;
    for(y=0;y<8;y++) {
        unsigned fg=bits[y],shade=(fg>>1)|(y?bits[y-1]|(bits[y-1]>>1):0);
        pixels[y*2]=pixels[y*2+1]=0;
        for(x=0;x<8;x++)pixels[y*2+(x>>2)]|=(u16)((fg&(128>>x)?3:shade&(128>>x)?1:0)<<((x&3)*4));
    }
    ((int (*)(const Rect *,const void *))0x8005adb8)(&rect,pixels);
    ((int (*)(int))0x8005ab0c)(0);
}
static void make_name(const u8 *name,const u8 *cache,u8 *out,u8 *bits) {
    unsigned i,j,c,first=*name,custom=first>=0x60 && first<0xc0 && (first-0x60)%6==0,unknown=1;
    unsigned actor=name[-2],count=0;
    for(i=0;i<6;i++) {
        if(name[i]!=255 && name[i]!=first+i)custom=0;
        if(name[i]!=0xcb)unknown=0;
    }
    custom=custom && cache_valid(cache);
    out[0]='~';out[1]='K';out[26]=0;
    for(i=0;i<6;i++) {
        c=unknown?'?':custom?(name[i]==255?0:r16(cache+16+(first-0x60+i)*2)):actor<64?DEFAULTS[actor*6+i]:0;
        if(c)count++;
        for(j=0;j<8;j++)bits[i*8+j]=0;
        if(c && c!=' ') {
            if(custom)copy(bits+i*8,cache+208+(first-0x60+i)*30+22,8);
            else for(j=0;j<PSX_NAME_GLYPHS;j++)if(r16(GLYPHS+j*10)==c) {copy(bits+i*8,GLYPHS+j*10+2,8);break;}
        }
        for(j=0;j<4;j++) {unsigned v=(c>>(12-j*4))&15;out[2+i*4+j]=(u8)(v<10?'0'+v:'A'+v-10);}
    }
    if(!count)out[0]=0;
}
u8 *kr_psx_name(const u8 *name) {
    unsigned start=(u32)name<0x80030000?0x8002f602:0x80034404;
    unsigned slot=((u32)name-start)/37,rank=(*(const u8 *)(start+0x24e + slot)>>3)&3,i;
    const u8 *cache=(const u8 *)(start==0x8002f602?0x80036000:0x80033500);
    u8 *bits=buffer()+0x2000+2880+rank*48;
    make_name(name,cache,OUTPUT,bits);copy(LAST,bits,48);LAST_RANK=rank;
    for(i=0;i<6;i++)upload(360+rank*6+i,bits+i*8);
    return OUTPUT;
}
int kr_psx_card_read(int port,const char *file,u8 *dest,unsigned length,unsigned offset) {
    PENDING=(u32)dest;
    (void)length;
    return ((int (*)(int,const char *,void *,unsigned,unsigned))0x80043af0)(port,file,buffer(),0x2000,offset);
}
void kr_psx_read_complete(void *context) {
    u8 *b=buffer(),*m=b+256,*p=b+512,*dest=(u8 *)PENDING;
    unsigned index=*(u16 *)((u8 *)context+0xea),i,j,sum=0,rank;
    if(!dest)return;
    PENDING=0;
    for(i=0;i<232;i++)sum+=m[i];
    if(index<15 && b[0]=='S' && b[1]=='C' && sum==*(u32 *)(m+232)) {
        for(i=0;i<16;i++)if(p[0x250+i] && (p[0x250+i]&7)==p[0x46d]) {
            u8 *bits=b+0x2000+index*192;
            rank=(p[0x250+i]>>3)&3;
            make_name(p+i*37+2,p+0x1100,m+rank*48,bits+rank*48);
            for(j=0;j<6;j++)upload(index*24+rank*6+j,bits+rank*48+j*8);
        }
        sum=0;for(i=0;i<232;i++)sum+=m[i];*(u32 *)(m+232)=sum;
    }
    copy(dest,b,512);
}
/* All four call sites pass the name as the fifth original printf argument.
 * Use the native renderer for positions, color and primitive ownership, then
 * route only these six letters to the separate Galmuri7 rectangle.
 */
int kr_psx_name_print(unsigned flags,int x,int y,const char *format,const u8 *text) {
    unsigned n,i,c,j,tile,drawn=0,offset=(u32)text-0x800ea950;
    u8 *state=*(u8 **)0x800ebd40,*entry;
    char output[7];unsigned count,result;
    if(text[0]!='~' || text[1]!='K')return ((int (*)(unsigned,int,int,const char *,const void *))0x800cc050)(flags,x,y,format,text);
    tile=offset<15*256 && (offset&255)<=144 && (offset&255)%48==0?(offset>>8)*24+((offset&255)/48)*6:360+LAST_RANK*6;
    for(i=0;i<6;i++) {
        c=0;for(j=0;j<4;j++) {n=text[2+i*4+j];c=(c<<4)|(n<='9'?n-'0':n-'A'+10);}
        output[i]=c?(c==' '?' ':'A'):0;
    }
    output[6]=0;count=*(u16 *)(state+2);
    result=((int (*)(unsigned,int,int,const char *,const void *))0x800cc050)(flags,x,y,format,output);
    for(i=0;i<6 && output[i];i++) {
        if(output[i]==' ')continue;
        entry=*(u8 **)0x800e8d10+(count+drawn++)*92;
        j=*(u32 *)(*(u32 *)0x800ebd3c+56);
        entry[36+j*20]=(u8)(((tile+i)&31)*8);entry[37+j*20]=(u8)(160+((tile+i)>>5)*8);
        *(u32 *)(entry+4)=(*(u32 *)(entry+4)&~15U)|8;
        *(u32 *)(entry+16)=(*(u32 *)(entry+16)&~15U)|8;
    }
    return result;
}
