#include "hangul_name.h"

#define NONE 255
static const u16 leads[19] = {
    0x3131,0x3132,0x3134,0x3137,0x3138,0x3139,0x3141,0x3142,0x3143,
    0x3145,0x3146,0x3147,0x3148,0x3149,0x314a,0x314b,0x314c,0x314d,0x314e
};
/* Values are Unicode compatibility jamo; the indexes are Hangul final indexes. */
static const u16 finals[28] = {
    0,0x3131,0x3132,0x3133,0x3134,0x3135,0x3136,0x3137,0x3139,
    0x313a,0x313b,0x313c,0x313d,0x313e,0x313f,0x3140,0x3141,
    0x3142,0x3144,0x3145,0x3146,0x3147,0x3148,0x314a,0x314b,0x314c,0x314d,0x314e
};
typedef struct { u8 first, second, result; } Pair;
static const Pair double_leads[] = {{0,0,1},{3,3,4},{7,7,8},{9,9,10},{12,12,13}};
static const Pair vowel_pairs[] = {
    {0,20,1},{2,20,3},{4,20,5},{6,20,7},{8,0,9},{8,1,10},{8,20,11},
    {9,20,10},{13,4,14},{13,5,15},{13,20,16},{14,20,15},{18,20,19}
};
static const Pair final_pairs[] = {
    {1,1,2},{1,19,3},{4,22,5},{4,27,6},{8,1,9},{8,16,10},{8,17,11},
    {8,19,12},{8,25,13},{8,26,14},{8,27,15},{17,19,18},{19,19,20}
};

static unsigned find(const u16 *array, unsigned count, unsigned value) {
    unsigned i;
    for (i=0;i<count;i++) if (array[i]==value) return i;
    return NONE;
}
static unsigned combine(const Pair *pairs, unsigned count, unsigned a, unsigned b) {
    unsigned i;
    for (i=0;i<count;i++)
        if (pairs[i].first==a && pairs[i].second==b) return pairs[i].result;
    return NONE;
}
static unsigned previous(const Pair *pairs, unsigned count, unsigned result) {
    unsigned i, value=NONE;
    /* Use the last spelling of a compound, matching incremental backspace. */
    for (i=0;i<count;i++) if (pairs[i].result==result) value=pairs[i].first;
    return value;
}
static unsigned current(const HangulName *s) {
    if (s->lead!=NONE && s->vowel!=NONE)
        return 0xac00+(s->lead*21+s->vowel)*28+s->final;
    if (s->lead!=NONE) return leads[s->lead];
    if (s->vowel!=NONE) return 0x314f+s->vowel;
    return 0;
}
static void commit(HangulName *s) {
    unsigned c=current(s);
    if (c && s->count<6) s->committed[s->count++]=(u16)c;
    s->lead=s->vowel=NONE;
    s->final=0;
}
void hn_init(HangulName *s, unsigned limit) {
    unsigned i;
    for (i=0;i<6;i++) s->committed[i]=0;
    s->count=s->final=0;
    s->lead=s->vowel=NONE;
    s->limit=limit<1?1:limit>6?6:(u8)limit;
}
int hn_feed(HangulName *s, unsigned c) {
    HangulName old=*s;
    unsigned l=find(leads,19,c), v=(c>=0x314f && c<=0x3163)?c-0x314f:NONE;
    unsigned value, t;
    /* The UI has no full-width whitespace key; normalize imported names too. */
    if (c==0x3000 || c==0xa0 || c==9) c=0x20;
    if (l!=NONE) {
        if (s->lead==NONE && s->vowel==NONE) s->lead=(u8)l;
        else if (s->lead!=NONE && s->vowel==NONE) {
            value=combine(double_leads,5,s->lead,l);
            if (value!=NONE) s->lead=(u8)value;
            else { commit(s); s->lead=(u8)l; }
        } else if (s->lead!=NONE && s->vowel!=NONE) {
            t=find(finals,28,c);
            if (!s->final && t!=NONE) s->final=(u8)t;
            else {
                value=combine(final_pairs,13,s->final,t);
                if (value!=NONE) s->final=(u8)value;
                else { commit(s); s->lead=(u8)l; }
            }
        } else { commit(s); s->lead=(u8)l; }
    } else if (v!=NONE) {
        if (s->final) {
            unsigned moved=s->final;
            value=previous(final_pairs,13,moved);
            if (value!=NONE && moved!=2 && moved!=20) {
                unsigned i;
                s->final=(u8)value;
                for (i=0;i<13;i++) if (final_pairs[i].result==moved) {
                    moved=final_pairs[i].second; break;
                }
            } else s->final=0;
            commit(s); s->lead=(u8)find(leads,19,finals[moved]); s->vowel=(u8)v;
        } else if (s->vowel==NONE) s->vowel=(u8)v;
        else {
            value=combine(vowel_pairs,13,s->vowel,v);
            if (value!=NONE) s->vowel=(u8)value;
            else { commit(s); s->vowel=(u8)v; }
        }
    } else {
        /* Only jamo, modern syllables, spaces and printable Latin are accepted. */
        if (!((c>=0xac00 && c<=0xd7a3) || (c>=0x20 && c<=0x7e))) return 0;
        commit(s);
        if (s->count<6) s->committed[s->count++]=(u16)c;
        else { *s=old; return 0; }
    }
    if (s->count+(current(s)!=0)>s->limit) { *s=old; return 0; }
    return 1;
}
void hn_backspace(HangulName *s) {
    unsigned c, n, value;
    if (!current(s)) {
        if (!s->count) return;
        c=s->committed[--s->count];
        if (c>=0xac00 && c<=0xd7a3) {
            n=c-0xac00; s->lead=(u8)(n/588); s->vowel=(u8)((n%588)/28); s->final=(u8)(n%28);
        } else {
            s->lead=(u8)find(leads,19,c);
            if (c>=0x314f && c<=0x3163) s->vowel=(u8)(c-0x314f);
            if (!current(s)) return;
        }
    }
    if (s->final) {
        value=previous(final_pairs,13,s->final); s->final=value==NONE?0:(u8)value;
    } else if (s->vowel!=NONE) s->vowel=(u8)previous(vowel_pairs,13,s->vowel);
    else if (s->lead!=NONE) s->lead=(u8)previous(double_leads,5,s->lead);
}
unsigned hn_text(const HangulName *s, u16 *output) {
    unsigned i, n=s->count, c=current(s);
    for (i=0;i<n;i++) output[i]=s->committed[i];
    if (c) output[n++]=(u16)c;
    output[n]=0;
    return n;
}
unsigned hn_confirm(const HangulName *s, u16 *output) {
    unsigned i, start=0, n=hn_text(s,output);
    while (start<n && output[start]==0x20) start++;
    while (n>start && output[n-1]==0x20) n--;
    for (i=start;i<n;i++) output[i-start]=output[i];
    output[n-start]=0;
    return n-start;
}
