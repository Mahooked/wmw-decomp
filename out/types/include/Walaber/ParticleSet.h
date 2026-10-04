// Recovered from Walaber::ParticleSet. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WALABER__PARTICLESET_H
#define WMW_WALABER__PARTICLESET_H

#include <stdint.h>

namespace Walaber {
struct ParticleSet {
    // size 80, align 8, confidence high
    uint64_t f_0x0;
    uint64_t f_0x8;
    uint8_t _pad24[8];
    uint64_t f_0x18;
    uint64_t f_0x20;
    uint64_t f_0x28;
    int32_t f_0x30;
    int32_t f_0x34;
    int32_t f_0x38;
    int32_t f_0x3c;
    uint8_t _pad72[8];
    uint64_t f_0x48;
};

}  // namespace Walaber
#endif
