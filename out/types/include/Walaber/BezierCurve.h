// Recovered from Walaber::BezierCurve. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WALABER__BEZIERCURVE_H
#define WMW_WALABER__BEZIERCURVE_H

#include <stdint.h>

namespace Walaber {
struct BezierCurve {
    // size 40, align 8, confidence high
    uint64_t f_0x0;
    uint64_t f_0x8;
    uint8_t _pad24[8];
    uint64_t f_0x18;
    int32_t f_0x20;
    int32_t f_0x24;
};

}  // namespace Walaber
#endif
