// Recovered from Walaber::Widget_ScrollableSet. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WALABER__WIDGET_SCROLLABLESET_H
#define WMW_WALABER__WIDGET_SCROLLABLESET_H

#include <stdint.h>

namespace Walaber {
struct Widget_ScrollableSet {
    // size 392, align 8, confidence high
    uint64_t f_0x0;
    uint8_t _pad256[248];
    uint64_t f_0x100;
    int32_t f_0x108;
    int32_t f_0x10c;
    int32_t f_0x110;
    int32_t f_0x114;
    float f_0x118;
    uint8_t _pad288[4];
    float f_0x120;
    int32_t f_0x124;
    int32_t f_0x128;
    uint8_t _pad304[4];
    int32_t f_0x130;
    float f_0x134;
    float f_0x138;
    uint8_t _pad320[4];
    uint64_t f_0x140;
    uint64_t f_0x148;
    uint8_t _pad344[8];
    uint64_t f_0x158;
    uint64_t f_0x160;
    uint8_t _pad368[8];
    uint64_t f_0x170;
    uint64_t f_0x178;
    uint8_t f_0x180;
    uint8_t _tail[7];
};

}  // namespace Walaber
#endif
