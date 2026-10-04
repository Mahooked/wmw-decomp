// Recovered from Walaber::Widget_ScrollableCamera. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WALABER__WIDGET_SCROLLABLECAMERA_H
#define WMW_WALABER__WIDGET_SCROLLABLECAMERA_H

#include <stdint.h>

namespace Walaber {
struct Widget_ScrollableCamera {
    // size 472, align 8, confidence high
    uint64_t f_0x0;
    uint8_t _pad256[248];
    uint64_t f_0x100;
    int32_t f_0x108;
    int32_t f_0x10c;
    float f_0x110;
    int32_t f_0x114;
    int32_t f_0x118;
    int32_t f_0x11c;
    float f_0x120;
    uint8_t _pad296[4];
    float f_0x128;
    uint8_t _pad304[4];
    int32_t f_0x130;
    uint8_t _pad320[12];
    uint64_t f_0x140;
    uint64_t f_0x148;
    uint8_t _pad344[8];
    uint64_t f_0x158;
    uint64_t f_0x160;
    uint8_t _pad368[8];
    uint64_t f_0x170;
    uint64_t f_0x178;
    uint8_t _pad392[8];
    uint64_t f_0x188;
    uint64_t f_0x190;
    uint8_t _pad416[8];
    uint64_t f_0x1a0;
    uint64_t f_0x1a8;
    uint8_t _pad440[8];
    uint64_t f_0x1b8;
    uint8_t _pad456[8];
    uint64_t f_0x1c8;
    uint64_t f_0x1d0;
};

}  // namespace Walaber
#endif
