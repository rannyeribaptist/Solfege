; This file is free software; as a special exception the author gives
; unlimited permission to copy and/or distribute it, with or without
; modifications, as long as this notice is preserved.
;
; This program is distributed in the hope that it will be useful, but
; WITHOUT ANY WARRANTY, to the extent permitted by law; without even the
; implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.

instr 1
    k1        linen     p4, p6, p3, p7      ; p4=amp
;  name           amplitude frequency wave-shape
    a1     oscil     k1,       p5,        1
           out       a1
endin
