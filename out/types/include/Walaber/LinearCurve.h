// Recovered from Walaber::LinearCurve. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WALABER__LINEARCURVE_H
#define WMW_WALABER__LINEARCURVE_H

#include <stdint.h>

namespace Walaber {
struct LinearCurve {
    // size 32, align 8, confidence high
    uint64_t f_0x0;
    uint8_t _pad24[16];
    uint64_t f_0x18;
};

}  // namespace Walaber
#endif
