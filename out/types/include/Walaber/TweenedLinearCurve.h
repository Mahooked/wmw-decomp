// Recovered from Walaber::TweenedLinearCurve. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WALABER__TWEENEDLINEARCURVE_H
#define WMW_WALABER__TWEENEDLINEARCURVE_H

#include <stdint.h>

namespace Walaber {
struct TweenedLinearCurve {
    // size 96, align 8, confidence high
    uint64_t f_0x0;
    uint64_t f_0x8;
    uint8_t _pad24[8];
    uint64_t f_0x18;
    int32_t f_0x20;
    int32_t f_0x24;
    int32_t f_0x28;
    uint8_t _pad48[4];
    uint64_t f_0x30;
    uint64_t f_0x38;
    uint64_t f_0x40;
    uint64_t f_0x48;
    uint64_t f_0x50;
    uint64_t f_0x58;
};

}  // namespace Walaber
#endif
