/* Map the original saved SwdTech alphabet without altering its save bytes. */
typedef unsigned char u8;
typedef unsigned short u16;
#define BYTE(a) (*(volatile u8 *)(a))
static void draw(unsigned cell) {
    volatile u16 *arg=*(volatile u16 **)0x8006c168;
    unsigned code=*arg&255,index=((const u16 *)0x8019d000)[code],base=0,space=index==223;
    if(!cell && code==255)return;
    if(index>=224) {index-=224;base=0x1340+(index>>8)*0x1600;index&=255;}
    *arg=index;
    BYTE(0x8002e0eb)=base;BYTE(0x8002e0ec)=base>>8;
    /* The editing grid keeps its six fixed cursor cells. Finished names use
       the ordinary half-width space while all visible glyphs stay 12px. */
    BYTE(0x8002e0b6)=!cell && space?6:12;
    ((void (*)(void))0x8011b048)();
}
void kr_swdtech_name(void) {draw(0);}
void kr_swdtech_cell(void) {draw(1);}
