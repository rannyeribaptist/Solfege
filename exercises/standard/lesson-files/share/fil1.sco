; This file is free software; as a special exception the author gives
; unlimited permission to copy and/or distribute it, with or without
; modifications, as long as this notice is preserved.
;
; This program is distributed in the hope that it will be useful, but
; WITHOUT ANY WARRANTY, to the extent permitted by law; without even the
; implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.


f1     0    4096 10   1    ; use GEN10 to compute a sine wave
; p1  p2    p3  p4     p5    p6     p7
;ins  strt  dur amp    freq  attack release
  i1  0     1   10000  440   0.2    0.08
  i1  +     1   10000  660   0.08    0.28
e                          ; indicate the "end" of the score
