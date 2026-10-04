// Recovered from Walaber::SoundEffectInstance. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WALABER__SOUNDEFFECTINSTANCE_H
#define WMW_WALABER__SOUNDEFFECTINSTANCE_H

#include <stdint.h>

namespace Walaber {
struct SoundEffectInstance {
    // size 80, align 8, confidence high
    uint8_t _pad8[8];
    uint64_t f_0x8;
    uint8_t _pad24[8];
    uint64_t f_0x18;
    uint8_t _pad44[12];
    float f_0x2c;
    uint8_t _pad72[24];
    uint8_t f_0x48;
    uint8_t _tail[7];
};

}  // namespace Walaber
#endif
