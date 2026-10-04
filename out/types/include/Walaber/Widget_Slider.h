// Recovered from Walaber::Widget_Slider. Offsets and element types come from load/store
// evidence in the binary; the names do not, and are inferred
// from the accessor symbols noted against them. Everything else
// is named after the offset it sits at.
#ifndef WMW_WALABER__WIDGET_SLIDER_H
#define WMW_WALABER__WIDGET_SLIDER_H

#include <stdint.h>

namespace Walaber {
struct Widget_Slider {
    // size 424, align 8, confidence high
    uint64_t f_0x0;
    uint8_t _pad144[136];
    float f_0x90;
    uint8_t _pad256[108];
    uint64_t f_0x100;
    uint8_t _pad328[64];
    float handleSize;  // named from setHandleSize
    uint8_t _pad336[4];
    float f_0x150;
    int32_t f_0x154;
    uint64_t stepSize;  // named from setStepSize
    uint8_t _pad360[8];
    float f_0x168;
    uint8_t _pad368[4];
    float f_0x170;
    float f_0x174;
    float f_0x178;
    float f_0x17c;
    uint8_t _pad388[4];
    uint8_t f_0x184;
    uint8_t _pad400[11];
    int32_t f_0x190;
    uint8_t _pad416[12];
    uint64_t f_0x1a0;
};

}  // namespace Walaber
#endif
