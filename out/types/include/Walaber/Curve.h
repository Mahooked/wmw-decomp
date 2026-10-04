// Recovered from Walaber::Curve. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WALABER__CURVE_H
#define WMW_WALABER__CURVE_H

#include <stdint.h>

namespace Walaber {
struct Curve {
    // size 48, align 8, confidence high
    uint64_t f_0x0;
    uint64_t f_0x8;
    uint64_t f_0x10;
    uint64_t f_0x18;
    int32_t f_0x20;
    int32_t f_0x24;
    int32_t f_0x28;
    float f_0x2c;
};

}  // namespace Walaber
#endif
