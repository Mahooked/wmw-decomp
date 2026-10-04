// Recovered from Walaber::NumericAnimationTrack. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WALABER__NUMERICANIMATIONTRACK_H
#define WMW_WALABER__NUMERICANIMATIONTRACK_H

#include <stdint.h>

namespace Walaber {
struct NumericAnimationTrack {
    // size 40, align 8, confidence high
    uint64_t f_0x0;
    uint8_t _pad16[8];
    int32_t f_0x10;
    uint8_t _pad24[4];
    uint64_t f_0x18;
    uint64_t f_0x20;
};

}  // namespace Walaber
#endif
