// Recovered from Walaber::Widget_Canvas. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WALABER__WIDGET_CANVAS_H
#define WMW_WALABER__WIDGET_CANVAS_H

#include <stdint.h>

namespace Walaber {
struct Widget_Canvas {
    // size 304, align 8, confidence high
    uint64_t f_0x0;
    uint8_t _pad256[248];
    uint64_t f_0x100;
    uint64_t f_0x108;
    int32_t f_0x110;
    uint8_t _pad284[8];
    int32_t f_0x11c;
    int32_t f_0x120;
    int32_t f_0x124;
    uint8_t f_0x128;
    uint8_t _tail[7];
};

}  // namespace Walaber
#endif
