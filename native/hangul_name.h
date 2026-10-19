#ifndef FF6_KR_HANGUL_NAME_H
#define FF6_KR_HANGUL_NAME_H

typedef unsigned char u8;
typedef unsigned short u16;

/* Six visible characters, with an uncommitted jamo/syllable at the end. */
typedef struct {
    u16 committed[6];
    u8 count, lead, vowel, final, limit;
} HangulName;

void hn_init(HangulName *state, unsigned limit);
int hn_feed(HangulName *state, unsigned character);
void hn_backspace(HangulName *state);
unsigned hn_text(const HangulName *state, u16 *output);
unsigned hn_confirm(const HangulName *state, u16 *output);

#endif
