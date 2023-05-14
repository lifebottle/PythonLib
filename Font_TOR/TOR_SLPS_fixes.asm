.ps2
.open "../../Data/Tales-Of-Rebirth/Disc/New/SLPS_254.50", 0x00FF000
    ;credits to Ethanol (he's the man) and SymphoniaLauren

    ; No smooshy (we don't like smooshy)
.org 0x105E18
    li v0, 0x1

    ;Cutscene Text Var Width fix
.org 0x11CC60
    ;sets bool flag for ascii to 0
    ori s4,zero,0x0


.org 0x11D494
    ;skips stright to the good stuff
    b        0x0011D4A4

.org 0x1CF680
;Shoves font blob into the exe (I'M SORRY KAJI)
      .incbin "fonttiles.bin"

.org 0x1CA240
;ASCII width table
;CHAR           L  R
/* ０ */ .byte   5, 5

/* １ */ .byte   6, 5

/* ２ */ .byte   5, 5

/* ３ */ .byte   5, 6

/* ４ */ .byte   4, 7

/* ５ */ .byte   6, 6

/* ６ */ .byte   6, 6

/* ７ */ .byte   6, 7

/* ８ */ .byte   4, 5

/* ９ */ .byte   4, 4

/* Ａ */ .byte   4, 6

/* Ｂ */ .byte   5, 6

/* Ｃ */ .byte   5, 6

/* Ｄ */ .byte   5, 6

/* Ｅ */ .byte   5, 7

/* Ｆ */ .byte   5, 8

/* Ｇ */ .byte   5, 7

/* Ｈ */ .byte   5, 7

/* Ｉ */ .byte   8, 9

/* Ｊ */ .byte   7, 8

/* Ｋ */ .byte   5, 6

/* Ｌ */ .byte   5, 8

/* Ｍ */ .byte   5, 5

/* Ｎ */ .byte   5, 6

/* Ｏ */ .byte   5, 5

/* Ｐ */ .byte   5, 6

/* Ｑ */ .byte   5, 5

/* Ｒ */ .byte   5, 7

/* Ｓ */ .byte   6, 7

/* Ｔ */ .byte   5, 7

/* Ｕ */ .byte   5, 6

/* Ｖ */ .byte   5, 6

/* Ｗ */ .byte   5, 3

/* Ｘ */ .byte   5, 7

/* Ｙ */ .byte   5, 8

/* Ｚ */ .byte   5, 5

/* ａ */ .byte   6, 8

/* ｂ */ .byte   6, 7

/* ｃ */ .byte   7, 8

/* ｄ */ .byte   6, 7

/* ｅ */ .byte   6, 7

/* ｆ */ .byte   7, 9

/* ｇ */ .byte   6, 7

/* ｈ */ .byte   6, 7

/* ｉ */ .byte   8, 9

/* ｊ */ .byte   9, 10

/* ｋ */ .byte   5, 7

/* ｌ */ .byte   9, 9

/* ｍ */ .byte   3, 5

/* ｎ */ .byte   6, 7

/* ｏ */ .byte   6, 7

/* ｐ */ .byte   6, 7

/* ｑ */ .byte   6, 7

/* ｒ */ .byte   7, 9

/* ｓ */ .byte   7, 8

/* ｔ */ .byte   7, 8

/* ｕ */ .byte   6, 7

/* ｖ */ .byte   5, 7

/* ｗ */ .byte   3, 4

/* ｘ */ .byte   6, 8

/* ｙ */ .byte   5, 7

/* ｚ */ .byte   6, 7

/* ， */ .byte   1, 15

/* ． */ .byte   1, 15

/* ・ */ .byte   6, 8

/* ： */ .byte   8, 8

/* ； */ .byte   7, 8

/* ？ */ .byte   4, 5

/* ！ */ .byte   7, 9

/* ／ */ .byte   0, 1

/* （ */ .byte   12, 1

/* ） */ .byte   1, 13

/* ［ */ .byte   13, 1

/* ］ */ .byte   1, 11

/* ｛ */ .byte   14, 1

/* ｝ */ .byte   1, 14

/* ＋ */ .byte   3, 6

/* － */ .byte   6, 7

/* ＝ */ .byte   4, 3

/* ＜ */ .byte   3, 3

/* ＞ */ .byte   3, 3

/* ％ */ .byte   2, 9

/* ＃ */ .byte   4, 4

/* ＆ */ .byte   2, 4

/* ＊ */ .byte   4, 4

/* ＠ */ .byte   0, 1

/* ｜ */ .byte   8, 8

/* ” */ .byte   1, 15

/* ’ */ .byte   1, 18

/* ＾ */ .byte   7, 6

/* 「 */ .byte   10, 1

/* 」 */ .byte   1, 11

/* 〜 */ .byte   5, 6

/* ＿ */ .byte   0, 0

/* 、 */ .byte   0, 13

/* 。 */ .byte   1, 12


.close