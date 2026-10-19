typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;
#define CFG ((const u32 *)0x800fff80)
#define WIDE ((u16 *)0x800ffb80)
#define PRINT_STATE ((u32 *)0x800fff8c)
extern void kr_omake_original_small_glyph(int,int,unsigned,unsigned,unsigned,void *);
extern int kr_omake_original_small_text(const u8 *,int,int,int,unsigned,unsigned);
extern void kr_omake_original_printf_glyph(unsigned);
void kr_omake_record_columns(unsigned flags,int x,int y,const u8 *source) {
    u8 labels[2][3];unsigned n=0,i;
    /* Half spaces must not pull the right-panel headings across its border. */
    while(*source && n<2) {
        unsigned c=*source++;
        if(c>=1 && c<=8 && *source>=0x80) {
            labels[n][0]=c;labels[n][1]=*source++;labels[n++][2]=0;
        }
    }
    if(n!=2)return;
    for(i=0;i<4;i++) {
        int column=x+(i&1?3:0)+(i>=2?13:0)+(i==3?1:0);
        ((void (*)(unsigned,int,int,const u8 *))0x800da4ac)(flags,column,y,labels[i&1]);
    }
}
static void small_packet(u8 *node,unsigned frame,unsigned index) {
    ((void (*)(void *,int,int,unsigned,void *))0x8005b9e0)(node+frame*12,0,0,0x19,0);
    node+=24+frame*20;node[12]=(index%36)*7;node[13]=CFG[7]+(index/36)*8;
    node[3]=4;node[7]=(node[7]&3)|0x64;*(u16 *)(node+16)=7;*(u16 *)(node+18)=8;
}
static void original_packet(u8 *node,unsigned frame,unsigned page) {
    ((void (*)(void *,int,int,unsigned,void *))0x8005b9e0)(node+frame*12,0,0,page,0);
    node+=24+frame*20;node[3]=3;node[7]=(node[7]&3)|0x74;
}

void kr_omake_attributes(int x,int y,unsigned mask) {
    const u16 *const *names=(const u16 *const *)CFG[6];unsigned i;
    *(u16 *)0x800f7de8=x;*(u16 *)0x800f7dea=y;
    if(!(mask&255)){((void (*)(int,int,int,unsigned))0x800e0dc4)(1,x,y,557);return;}
    for(i=0;i<8;i++)if(mask&(1<<i)) {
        const u16 *p=names[i];
        while(*p!=0xffff)((void (*)(unsigned))0x800e0ad0)(*p++);
        *(u16 *)0x800f7de8+=4;
    }
}

void kr_omake_printf_glyph(unsigned glyph) {
    u8 *state=*(u8 **)0x800f967c;
    unsigned key=*(u32 *)(state+0x18),count=*(u16 *)(state+2);
    int shift=PRINT_STATE[0]==key?(int)PRINT_STATE[1]:0;
    if(glyph==32) {
        ++*(u16 *)(state+0x18);shift-=4;
    }else {
        unsigned frame=*(u32 *)(*(u32 *)0x800f9678+0x38),index=glyph-0x1000;
        u8 *node=*(u8 **)0x800f4fc4+count*92,*sprite=node+24+frame*20;
        kr_omake_original_printf_glyph(glyph>=0x1000?'A':glyph);
        if(glyph>=0x1000)small_packet(node,frame,index);
        else original_packet(node,frame,*(u16 *)(state+8));
        *(u16 *)(sprite+8)+=shift;
    }
    PRINT_STATE[0]=*(u32 *)(state+0x18);PRINT_STATE[1]=shift;
}
unsigned kr_omake_puts(const u8 *source) {
    unsigned count=0;
    while(*source) {
        unsigned c=*source++;
        if(c>=1 && c<=8 && *source>=0x80) {
            unsigned id=((c-1)<<7)|(*source++&127);
            if(id<CFG[2])count+=kr_omake_puts(((const u8 *const *)CFG[0])[id]);
        }else {
            if(c>=0x10 && c<=0x1f)c=0x1000+((c-0x10)<<7)+(*source++&127);
            kr_omake_printf_glyph(c);count++;
        }
    }
    return count;
}
void kr_omake_printf_ref(unsigned first,unsigned second) {
    u8 source[3];source[0]=first;source[1]=second;source[2]=0;
    kr_omake_puts(source);
}

u16 *kr_omake_get_text(unsigned offset) {
    const u8 *p=*(const u8 **)(0x800f3930+offset);
    const u16 *h=(const u16 *)CFG[1];const u8 *symbols=(const u8 *)(h+48);
    unsigned remaining=p[0]|(p[1]<<8),bits=0,nbit=0;u8 *out=(u8 *)WIDE;p+=2;
    while(remaining--) {
        unsigned code=0,length=0;
        do {
            if(!nbit){bits=*p++;nbit=8;}
            code=(code<<1)|((bits>>7)&1);bits<<=1;nbit--;length++;
        }while(code<h[16+length] || code>=h[16+length]+h[length]);
        *out++=symbols[h[32+length]+code-h[16+length]];
    }
    return WIDE;
}
unsigned kr_omake_text_length(unsigned id) {
    const u16 *p=kr_omake_get_text(id*4);unsigned width=0,max=0;
    while(*p!=0xffff){unsigned c=*p++;if(c==0x8000){if(width>max)max=width;width=0;}else width+=c?12:6;}
    if(width>max)max=width;
    return (max+11)/12;
}
void kr_omake_small_glyph(int x,int y,unsigned glyph,unsigned palette,unsigned depth,void *buffer) {
    unsigned count,frame,index;u8 *node;
    index=glyph-0x1000;
    count=*(const u16 *)(*(const u32 *)0x800f967c+2);
    kr_omake_original_small_glyph(x,y,glyph>=0x1000?'A':glyph,palette,depth,buffer);
    frame=*(const u32 *)(*(const u32 *)0x800f9678+0x38);
    node=(u8 *)buffer+count*92;
    if(glyph>=0x1000)small_packet(node,frame,index);
    else original_packet(node,frame,*(u16 *)(*(const u32 *)0x800f967c+8));
}
int kr_omake_small_text(const u8 *source,int x,int y,int columns,unsigned palette,unsigned depth) {
    u8 expanded[512];unsigned n=0,count=0,has_ref=0,previous=PRINT_STATE[2];int result;const u8 *p=source;
    while(*p && n<sizeof(expanded)-3) {
        unsigned c=*p++;
        if(c>=1 && c<=8 && *p>=0x80) {
            unsigned id=((c-1)<<7)|(*p++&127);
            if(id>=CFG[2]) {expanded[n++]=c;expanded[n++]=p[-1];count+=2;continue;}
            const u8 *text=((const u8 *const *)CFG[0])[id];has_ref=1;
            while(*text && n<sizeof(expanded)-3) {
                unsigned d=*text++;expanded[n++]=d;
                if(d>=0x10 && d<=0x1f)expanded[n++]=*text++;
                count++;
            }
        }else {expanded[n++]=c;count++;}
    }
    expanded[n]=0;
    /* Native windows encode empty panel cells as spaces in a border template. */
    PRINT_STATE[2]=!has_ref && *source=='(';
    if(!has_ref){result=kr_omake_original_small_text(source,x,y,columns,palette,depth);PRINT_STATE[2]=previous;return result;}
    if((unsigned)columns<count)columns=count;
    result=kr_omake_original_small_text(expanded,x,y,columns,palette,depth);PRINT_STATE[2]=previous;return result;
}
