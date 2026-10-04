// Recovered from Walaber::FluidParticleSet. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WALABER__FLUIDPARTICLESET_H
#define WMW_WALABER__FLUIDPARTICLESET_H

#include <stdint.h>

namespace Walaber {
struct FluidParticleSet {
    // size 56, align 8, confidence high
    uint64_t f_0x0;
    uint8_t _pad32[24];
    uint64_t f_0x20;
    uint64_t f_0x28;
    int32_t f_0x30;
    int32_t f_0x34;
};

}  // namespace Walaber
#endif
