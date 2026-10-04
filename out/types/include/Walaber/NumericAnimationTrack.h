// Recovered from Walaber::NumericAnimationTrack. Offsets and element types come from load/store
// evidence in the binary; the names do not, and are inferred
// from the accessor symbols noted against them. Everything else
// is named after the offset it sits at.
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
    uint64_t animation;  // named from setAnimation
};

}  // namespace Walaber
#endif
