// Recovered from Walaber::BaseParticle. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WALABER__BASEPARTICLE_H
#define WMW_WALABER__BASEPARTICLE_H

#include <stdint.h>

namespace Walaber {
struct BaseParticle {
    // size 28, align 4, confidence high
    int32_t f_0x0;
    int32_t f_0x4;
    int32_t f_0x8;
    int32_t f_0xc;
    uint8_t _pad24[8];
    int32_t f_0x18;
};

}  // namespace Walaber
#endif
