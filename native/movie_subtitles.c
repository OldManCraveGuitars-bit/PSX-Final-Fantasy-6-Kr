/* Independent, frame-timed GPU captions. Original STR/MDEC data stays intact. */
typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;
#include "movie-bank-routes.h"
#define DATA ((u8 *)0x80033000)
#define PIXELS ((u8 *)0x80034000)
#define META ((u32 *)0x80033fe0)
#define CALLBACK (*(u32 *)0x8006c054)
typedef struct { short x,y,w,h; } Rect;
extern int kr_movie_original(u32 *,int,int,int);

int kr_movie_caption(int a,int b) {
    unsigned frame=META[2]?META[2]-1:0,i,x,y,line,rows=1;
    const u8 *cue=DATA+8,*text=0,*next;
    int result=META[0]?((int (*)(int,int))META[0])(a,b):0;
    for(i=0;i<DATA[0];i++,cue+=6) {
        unsigned start=cue[0]|(cue[1]<<8),end=cue[2]|(cue[3]<<8);
        if(frame>=start && frame<end) {text=DATA+(cue[4]|(cue[5]<<8));break;}
    }
    if(!text)return result;
    for(i=0;text[i];i++)if(text[i]==254)rows++;
    for(line=0;line<rows;line++) {
    unsigned width=0;
    for(next=text;*next && *next!=254;next++)width+=*next==1?6:12;
    for(i=0;i<13440;i++)PIXELS[i]=0;
    x=(320-width)/2;
    for(i=0;text+i<next;i++) {
        unsigned c=text[i];
        if(c!=1) for(y=0;y<12;y++) {
            unsigned bits=((const u16 *)(DATA+(DATA[4]|(DATA[5]<<8))))[(c-2)*12+y],k;
            for(k=0;k<12;k++) if(bits&(2048>>k)) {
                unsigned p=((y+1)*320+x+k)*3;
                PIXELS[p]=PIXELS[p+1]=PIXELS[p+2]=255;
            }
        }
        x+=c==1?6:12;
    }
    {
        Rect rect={0,(short)(220-(rows-1-line)*14),480,14};
        void (*sync)(int)=(void *)0x8005ab0c;
        void (*load)(Rect *,void *)=(void *)0x8005adb8;
        sync(0);load(&rect,PIXELS);rect.y+=256;load(&rect,PIXELS);sync(0);
    }
    text=*next?next+1:next;
    }
    return result;
}

int kr_movie_play(u32 *params,int a,int b,int c) {
    u32 backup[4608],i,msf=MOVIE_OPERA_MSF;
    int result;
    if(*(const u32 *)params[0]==0x00043907)msf=MOVIE_OPEN_MSF;
    else if(*(const u32 *)params[0]==0x00681114)msf=MOVIE_END_MSF;
    else if(*(const u32 *)params[0]!=0x00601521)return kr_movie_original(params,a,b,c);
    for(i=0;i<4608;i++)backup[i]=((volatile u32 *)DATA)[i];
    ((void (*)(void *,int,const void *))0x8004d2d8)(DATA,2,&msf);
    /* FMV setup has replaced the ordinary VBlank queue dispatcher. */
    while(((int (*)(int))0x800460c0)(0x40)) {
        ((void (*)(void))0x800470b8)();
        ((void (*)(int))0x80059820)(0);
    }
    if(DATA[0]>64 || DATA[1]!='K' || DATA[2]!='R' || DATA[3]!=2) {
        for(i=0;i<4608;i++)((volatile u32 *)DATA)[i]=backup[i];
        return kr_movie_original(params,a,b,c);
    }
    META[0]=CALLBACK;META[1]=(u32)params;META[2]=META[3]=0;CALLBACK=(u32)kr_movie_caption;
    result=kr_movie_original(params,a,b,c);
    CALLBACK=META[0];
    for(i=0;i<4608;i++)((volatile u32 *)DATA)[i]=backup[i];
    return result;
}
