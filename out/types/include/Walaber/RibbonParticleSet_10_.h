// Recovered from Walaber::RibbonParticleSet<10>. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WALABER__RIBBONPARTICLESET_10__H
#define WMW_WALABER__RIBBONPARTICLESET_10__H

#include <stdint.h>

namespace Walaber {
struct RibbonParticleSet<10> {
    // size 104, align 8, confidence high
    uint64_t f_0x0;
    uint8_t _pad32[24];
    uint64_t f_0x20;
    uint64_t f_0x28;
    int32_t f_0x30;
    int32_t f_0x34;
    uint8_t _pad68[12];
    int32_t f_0x44;
    uint64_t f_0x48;
    uint64_t f_0x50;
    uint64_t f_0x58;
    uint64_t f_0x60;
};

}  // namespace Walaber
#endif
