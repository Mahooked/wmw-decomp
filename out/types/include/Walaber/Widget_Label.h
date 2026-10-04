// Recovered from Walaber::Widget_Label. Offsets and element types come from load/store
// evidence in the binary; the names do not, and are inferred
// from the accessor symbols noted against them. Everything else
// is named after the offset it sits at.
#ifndef WMW_WALABER__WIDGET_LABEL_H
#define WMW_WALABER__WIDGET_LABEL_H

#include <stdint.h>

namespace Walaber {
struct Widget_Label {
    // size 392, align 8, confidence high
    uint8_t f_0x0;
    uint8_t _pad144[143];
    float f_0x90;
    float f_0x94;
    uint8_t _pad232[80];
    uint64_t f_0xe8;
    uint64_t f_0xf0;
    float f_0xf8;
    float f_0xfc;
    float f_0x100;
    uint8_t _pad264[4];
    int32_t f_0x108;
    uint8_t _pad272[4];
    uint64_t f_0x110;
    uint64_t f_0x118;
    double tileOffset;  // named from setTileOffset
    double f_0x128;
    uint64_t f_0x130;
    uint64_t tileAnimation;  // named from setTileAnimation
    uint8_t f_0x140;
    uint8_t f_0x141;
    uint8_t f_0x142;
    uint8_t f_0x143;
    uint8_t f_0x144;
    uint8_t f_0x145;
    uint8_t f_0x146;
    uint8_t f_0x147;
    float f_0x148;
    float f_0x14c;
    float f_0x150;
    float f_0x154;
    int32_t f_0x158;
    float f_0x15c;
    uint8_t _pad356[4];
    int32_t f_0x164;
    uint64_t f_0x168;
    uint64_t f_0x170;
    uint64_t f_0x178;
    uint64_t f_0x180;
};

}  // namespace Walaber
#endif
