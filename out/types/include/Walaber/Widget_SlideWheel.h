// Recovered from Walaber::Widget_SlideWheel. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WALABER__WIDGET_SLIDEWHEEL_H
#define WMW_WALABER__WIDGET_SLIDEWHEEL_H

#include <stdint.h>

namespace Walaber {
struct Widget_SlideWheel {
    // size 328, align 8, confidence high
    uint8_t _pad284[284];
    float f_0x11c;
    uint8_t _pad296[8];
    uint64_t f_0x128;
    float f_0x130;
    uint8_t _pad312[4];
    uint64_t f_0x138;
    uint64_t f_0x140;
};

}  // namespace Walaber
#endif
