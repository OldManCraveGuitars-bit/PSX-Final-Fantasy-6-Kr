"""Reference Hangul composition state machine for the controller name editor.

This is the input core; native game UI/save integration is a separate step.
"""
import unicodedata

LEADS=list('ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ')
VOWELS=list('ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ')
FINALS=['']+list('ㄱㄲㄳㄴㄵㄶㄷㄹㄺㄻㄼㄽㄾㄿㅀㅁㅂㅄㅅㅆㅇㅈㅊㅋㅌㅍㅎ')
DOUBLE={('ㄱ','ㄱ'):'ㄲ',('ㄷ','ㄷ'):'ㄸ',('ㅂ','ㅂ'):'ㅃ',('ㅅ','ㅅ'):'ㅆ',('ㅈ','ㅈ'):'ㅉ'}
V_COMBINE={('ㅏ','ㅣ'):'ㅐ',('ㅑ','ㅣ'):'ㅒ',('ㅓ','ㅣ'):'ㅔ',('ㅕ','ㅣ'):'ㅖ',('ㅗ','ㅏ'):'ㅘ',('ㅗ','ㅐ'):'ㅙ',('ㅗ','ㅣ'):'ㅚ',('ㅘ','ㅣ'):'ㅙ',('ㅜ','ㅓ'):'ㅝ',('ㅜ','ㅔ'):'ㅞ',('ㅜ','ㅣ'):'ㅟ',('ㅝ','ㅣ'):'ㅞ',('ㅡ','ㅣ'):'ㅢ'}
T_COMBINE={('ㄱ','ㄱ'):'ㄲ',('ㄱ','ㅅ'):'ㄳ',('ㄴ','ㅈ'):'ㄵ',('ㄴ','ㅎ'):'ㄶ',('ㄹ','ㄱ'):'ㄺ',('ㄹ','ㅁ'):'ㄻ',('ㄹ','ㅂ'):'ㄼ',('ㄹ','ㅅ'):'ㄽ',('ㄹ','ㅌ'):'ㄾ',('ㄹ','ㅍ'):'ㄿ',('ㄹ','ㅎ'):'ㅀ',('ㅂ','ㅅ'):'ㅄ',('ㅅ','ㅅ'):'ㅆ'}
T_SPLIT={v:k for k,v in T_COMBINE.items() if v not in ('ㄲ','ㅆ')}
V_BACK={v:k[0] for k,v in V_COMBINE.items()}
T_BACK={v:k[0] for k,v in T_COMBINE.items()}
L_BACK={v:k[0] for k,v in DOUBLE.items()}

class HangulName:
    def __init__(self,limit=6):
        self.limit=limit;self.done=[];self.l=self.v=self.t=''
    def current(self):
        if self.l and self.v:
            return chr(0xac00+(LEADS.index(self.l)*21+VOWELS.index(self.v))*28+FINALS.index(self.t))
        return self.l or self.v
    @property
    def text(self):return ''.join(self.done)+self.current()
    def _commit(self):
        if self.current():self.done.append(self.current())
        self.l=self.v=self.t=''
    def feed(self,key):
        key=unicodedata.normalize('NFC',key)
        if len(key)!=1:raise ValueError('One selected character is required')
        before=(self.done.copy(),self.l,self.v,self.t)
        if key in LEADS:
            if not self.l and not self.v:self.l=key
            elif self.l and not self.v:
                if (self.l,key) in DOUBLE:self.l=DOUBLE[self.l,key]
                else:self._commit();self.l=key
            elif self.l and self.v:
                if not self.t and key in FINALS:self.t=key
                elif (self.t,key) in T_COMBINE:self.t=T_COMBINE[self.t,key]
                else:self._commit();self.l=key
            else:self._commit();self.l=key
        elif key in VOWELS:
            if self.t:
                old=self.t
                if old in T_SPLIT:self.t,new_l=T_SPLIT[old]
                else:self.t='';new_l=old
                self._commit();self.l=new_l;self.v=key
            elif not self.v:self.v=key
            elif (self.v,key) in V_COMBINE:self.v=V_COMBINE[self.v,key]
            else:self._commit();self.v=key
        else:
            self._commit();self.done.append(' ' if key.isspace() else key)
        if len(self.text)>self.limit:
            self.done,self.l,self.v,self.t=before
            return False
        return True
    def _restore_last(self):
        if not self.done:return False
        c=self.done.pop();n=ord(c)-0xac00
        if 0<=n<11172:
            self.l=LEADS[n//588];self.v=VOWELS[(n%588)//28];self.t=FINALS[n%28]
        elif c in LEADS:self.l=c
        elif c in VOWELS:self.v=c
        else:return False
        return True
    def backspace(self):
        if not self.current() and not self._restore_last():return
        if self.t:self.t=T_BACK.get(self.t,'')
        elif self.v:self.v=V_BACK.get(self.v,'')
        elif self.l:self.l=L_BACK.get(self.l,'')
    def confirm(self):
        value=unicodedata.normalize('NFC',self.text).strip(' ')
        if not value:raise ValueError('Name is empty')
        return value

if __name__=='__main__':
    name=HangulName()
    for c in 'ㅎㅏㄴㄱㅡㄹ':name.feed(c)
    print(name.confirm())
