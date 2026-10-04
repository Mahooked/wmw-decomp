// Recovered from Walaber::Rect. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WALABER__RECT_H
#define WMW_WALABER__RECT_H

#include <stdint.h>

namespace Walaber {
struct Rect {
    // size 16, align 4, confidence high
    float f_0x0;
    float f_0x4;
    float f_0x8;
    float f_0xc;
};

}  // namespace Walaber
#endif
