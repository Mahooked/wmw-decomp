// Recovered from Walaber::Widget. Offsets and element types come from load/store
// evidence in the binary; the names do not, and are inferred
// from the accessor symbols noted against them. Everything else
// is named after the offset it sits at.
#ifndef WMW_WALABER__WIDGET_H
#define WMW_WALABER__WIDGET_H

#include <stdint.h>

namespace Walaber {
struct Widget {
    // size 344, align 8, confidence high
    uint64_t f_0x0;
    uint64_t f_0x8;
    uint8_t _pad24[8];
    uint64_t f_0x18;
    uint8_t _pad128[96];
    int32_t f_0x80;
    int32_t f_0x84;
    int32_t angle;  // named from _getAngle
    uint16_t f_0x8c;
    uint8_t _pad144[2];
    float baseSize;  // named from setBaseSize
    float f_0x94;
    uint64_t f_0x98;
    uint8_t _pad168[8];
    int32_t f_0xa8;
    int32_t f_0xac;
    uint8_t f_0xb0;
    uint8_t _pad180[3];
    uint32_t f_0xb4;
    uint8_t _pad196[12];
    int32_t f_0xc4;
    uint64_t widgetMgr;  // named from setWidgetMgr
    uint8_t _pad232[24];
    uint64_t f_0xe8;
    uint64_t f_0xf0;
    int32_t f_0xf8;
    uint8_t _pad256[4];
    uint64_t f_0x100;
    uint8_t _pad336[72];
    uint8_t f_0x150;
    uint8_t _tail[7];
};

}  // namespace Walaber
#endif
