// Recovered from Walaber::ParticleEmitter::EmitterZone. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WALABER__PARTICLEEMITTER__EMITTERZONE_H
#define WMW_WALABER__PARTICLEEMITTER__EMITTERZONE_H

#include <stdint.h>

namespace Walaber {
namespace ParticleEmitter {
struct EmitterZone {
    // size 32, align 8, confidence med
    uint64_t f_0x0;
    uint64_t f_0x8;
    int32_t f_0x10;
    uint32_t f_0x14;
    uint8_t _tail[8];
};

}  // namespace Walaber::ParticleEmitter
#endif
