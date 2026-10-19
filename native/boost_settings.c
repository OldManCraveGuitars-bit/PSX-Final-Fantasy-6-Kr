/* Native configuration subpage. The original menu still owns its window,
 * graphics buffers, input polling, fade, and return-to-field lifecycle. */
typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;
typedef struct {short x,y,w,h;} Rect;
#define BOOST __attribute__((section(".boost")))
#define DATA __attribute__((section(".boost_data")))
#define STATE __attribute__((section(".boost_state")))
#define BYTE(a) (*(volatile u8 *)(a))
#define WORD(a) (*(volatile u16 *)(a))
#include "boost-text-data.h"
extern void kr_boost_line(unsigned,unsigned,unsigned,const u16 *);
extern void kr_boost_header(const u16 *);
static u8 active STATE=0,selected STATE=0,saved_cursor_flags STATE=0,last_page STATE=0;
static const u16 * const labels[4] DATA={kr_boost_text_encounter,kr_boost_text_exp,kr_boost_text_gil,kr_boost_text_ap};
static const u16 * const magic_types[3] DATA={kr_boost_text_magic_recovery,kr_boost_text_magic_attack,kr_boost_text_magic_effect};
static const u16 * const ranks[3] DATA={kr_boost_text_rank1,kr_boost_text_rank2,kr_boost_text_rank3};
void BOOST kr_config_magic(void) {
    Rect rect={440,304,56,48};unsigned i,index=BYTE(0x8002fd54)&7;
    const u8 *permutation=(const u8 *)0x8012b488+(index<6?index:0)*4;
    ((int (*)(int))0x8005ab0c)(0);
    ((int (*)(const Rect *,int,int,int))0x8005ac90)(&rect,0,0,0);
    for(i=0;i<3;i++) {
        kr_boost_line(14,39+i*2,0x2000,ranks[i]);
        kr_boost_line(17,39+i*2,0x2000,magic_types[permutation[i]/4]);
    }
}
static unsigned BOOST flags(void) {
    return ((unsigned (*)(void))KR_BOOST_FLAGS_ADDRESS)();
}
static void BOOST store(unsigned value) {
    unsigned i;u8 *header=(u8 *)0x80030708;
    value&=15;
    *(u32 *)header=0x31545342U;
    *(u32 *)(header+4)=value|((value^0xa5)<<8);
    for(i=0;i<8;i++)((u8 *)0x80036008)[i]=header[i];
}
static void BOOST draw(void) {
    Rect rect={256,256,256,256};unsigned i,value=flags();
    ((int (*)(int))0x8005ab0c)(0);
    ((int (*)(const Rect *,int,int,int))0x8005ac90)(&rect,0,0,0);
    kr_boost_line(3,5,0x2400,kr_boost_text_title);
    for(i=0;i<4;i++) {
        if(i==selected)kr_boost_line(2,7+i*3,0x2000,kr_boost_text_cursor);
        kr_boost_line(4,7+i*3,0x2000,labels[i]);
        kr_boost_line(18,7+i*3,!(value&(1<<i))?0x2400:0x2800,kr_boost_text_off);
        kr_boost_line(24,7+i*3,(value&(1<<i))?0x2400:0x2800,kr_boost_text_on);
    }
    kr_boost_line(3,20,0x2000,kr_boost_text_controls);
    kr_boost_line(3,22,0x2000,kr_boost_text_back);
    ((int (*)(int))0x8005ab0c)(0);
}
void BOOST kr_boost_config_init(void) {
    active=selected=last_page=0;
    ((void (*)(void))0x800c949c)();
    ((void (*)(void))0x800d8390)();
    kr_boost_header(kr_boost_text_hint);
    ((void (*)(void))0x800d83f8)();
}
void BOOST kr_boost_config_tick(void) {
    unsigned high=BYTE(0x8002e009),low=BYTE(0x8002e008);
    unsigned value=flags(),changed=0,old=selected;
    if(!active) {
        if(!(low&0x10)) {
            /* The native scroll task restores its cached BG1 canvas after
             * initialization. Redraw once when control returns on page 2,
             * before processing input that might start another transition. */
            unsigned page=BYTE(0x8002e04a);
            if(page!=last_page) { last_page=page;if(page)kr_config_magic(); }
            ((void (*)(void))0x800cd0c8)();return;
        }
        active=1;selected=0;saved_cursor_flags=BYTE(0x8002e046);
        BYTE(0x8002e046)|=6;
        WORD(0x8002e03f)=0xfffb; /* Show first native BG1 canvas page. */
        ((void (*)(void))0x800fca90)();draw();return;
    }
    ((void (*)(void))0x800fcc68)();
    if((high&0x80) || (low&0x10)) {
        BYTE(0x8002e046)=saved_cursor_flags;active=0;
        ((void (*)(void))0x800fca48)();kr_boost_config_init();return;
    }
    if(high&8)selected=(selected+3)&3;
    else if(high&4)selected=(selected+1)&3;
    if(high&2) { value&=~(1<<selected);changed=1; }
    else if(high&1) { value|=1<<selected;changed=1; }
    else if(low&0x80) { value^=1<<selected;changed=1; }
    if(changed)store(value);
    if(changed || selected!=old) { ((void (*)(void))0x800fc9c4)();draw(); }
}
