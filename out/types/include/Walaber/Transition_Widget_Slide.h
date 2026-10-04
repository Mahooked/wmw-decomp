// Recovered from Walaber::Transition_Widget_Slide. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WALABER__TRANSITION_WIDGET_SLIDE_H
#define WMW_WALABER__TRANSITION_WIDGET_SLIDE_H

#include <stdint.h>

namespace Walaber {
struct Transition_Widget_Slide {
    // size 304, align 8, confidence high
    uint8_t f_0x0;
    uint8_t _pad112[111];
    float f_0x70;
    float f_0x74;
    float f_0x78;
    uint8_t _pad129[5];
    uint8_t f_0x81;
    uint8_t f_0x82;
    uint8_t _pad196[65];
    uint8_t f_0xc4;
    uint8_t _pad198[1];
    uint8_t f_0xc6;
    uint8_t _pad200[1];
    double f_0xc8;
    double f_0xd0;
    double f_0xd8;
    uint64_t f_0xe0;
    uint64_t f_0xe8;
    double f_0xf0;
    float f_0xf8;
    float f_0xfc;
    float f_0x100;
    float f_0x104;
    int32_t f_0x108;
    uint8_t _pad272[4];
    int32_t f_0x110;
    uint8_t f_0x114;
    uint8_t _pad280[3];
    uint64_t f_0x118;
    uint64_t f_0x120;
    uint64_t f_0x128;
};

}  // namespace Walaber
#endif
