// Recovered from Walaber::Widget_Spinner. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WALABER__WIDGET_SPINNER_H
#define WMW_WALABER__WIDGET_SPINNER_H

#include <stdint.h>

namespace Walaber {
struct Widget_Spinner {
    // size 312, align 8, confidence high
    uint8_t _pad296[296];
    float f_0x128;
    uint8_t _pad304[4];
    uint64_t f_0x130;
};

}  // namespace Walaber
#endif
