// Recovered from Walaber::Widget_ColorPicker. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WALABER__WIDGET_COLORPICKER_H
#define WMW_WALABER__WIDGET_COLORPICKER_H

#include <stdint.h>

namespace Walaber {
struct Widget_ColorPicker {
    // size 424, align 8, confidence high
    uint8_t f_0x0;
    uint8_t _pad144[143];
    float f_0x90;
    uint8_t _pad240[92];
    double f_0xf0;
    uint8_t _pad252[4];
    int32_t f_0xfc;
    int32_t f_0x100;
    uint8_t _pad264[4];
    uint64_t f_0x108;
    float f_0x110;
    float f_0x114;
    float f_0x118;
    uint8_t _pad288[4];
    uint8_t f_0x120;
    uint8_t _pad292[3];
    int32_t f_0x124;
    int32_t f_0x128;
    uint16_t f_0x12c;
    uint8_t _pad304[2];
    uint64_t f_0x130;
    uint64_t f_0x138;
    uint64_t f_0x140;
    uint64_t f_0x148;
    uint64_t f_0x150;
    uint64_t f_0x158;
    double f_0x160;
    double f_0x168;
    uint64_t f_0x170;
    uint64_t f_0x178;
    uint64_t f_0x180;
    uint64_t f_0x188;
    uint64_t f_0x190;
    uint64_t f_0x198;
    float f_0x1a0;
    uint8_t _tail[4];
};

}  // namespace Walaber
#endif
