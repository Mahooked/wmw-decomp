// Recovered from Walaber::Widget_Toggle. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WALABER__WIDGET_TOGGLE_H
#define WMW_WALABER__WIDGET_TOGGLE_H

#include <stdint.h>

namespace Walaber {
struct Widget_Toggle {
    // size 424, align 8, confidence high
    uint64_t f_0x0;
    uint8_t _pad144[136];
    float f_0x90;
    uint8_t _pad232[84];
    uint64_t f_0xe8;
    uint64_t f_0xf0;
    uint8_t _pad256[8];
    uint64_t f_0x100;
    uint64_t f_0x108;
    uint64_t f_0x110;
    uint64_t f_0x118;
    uint64_t f_0x120;
    uint64_t f_0x128;
    uint64_t f_0x130;
    uint64_t f_0x138;
    uint64_t f_0x140;
    uint64_t f_0x148;
    float f_0x150;
    uint8_t _pad344[4];
    uint64_t f_0x158;
    uint64_t f_0x160;
    uint8_t f_0x168;
    uint8_t _pad376[15];
    uint64_t f_0x178;
    uint8_t f_0x180;
    uint8_t _pad400[15];
    uint64_t f_0x190;
    float f_0x198;
    uint8_t f_0x19c;
    uint8_t _pad416[3];
    int32_t f_0x1a0;
    uint8_t f_0x1a4;
    uint8_t f_0x1a5;
    uint8_t _tail[2];
};

}  // namespace Walaber
#endif
