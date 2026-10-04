// Recovered from Walaber::SoundEffectInstance. Offsets and element types come from load/store
// evidence in the binary; the names do not, and are inferred
// from the accessor symbols noted against them. Everything else
// is named after the offset it sits at.
#ifndef WMW_WALABER__SOUNDEFFECTINSTANCE_H
#define WMW_WALABER__SOUNDEFFECTINSTANCE_H

#include <stdint.h>

namespace Walaber {
struct SoundEffectInstance {
    // size 80, align 8, confidence high
    uint8_t _pad8[8];
    uint64_t f_0x8;
    uint8_t _pad24[8];
    uint64_t playbackPosition;  // named from getPlaybackPosition
    uint8_t _pad44[12];
    float f_0x2c;
    uint8_t _pad72[24];
    uint8_t state;  // named from getState
    uint8_t _tail[7];
};

}  // namespace Walaber
#endif
