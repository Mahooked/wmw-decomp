// Recovered from Walaber::SpriteAnimationTrack. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WALABER__SPRITEANIMATIONTRACK_H
#define WMW_WALABER__SPRITEANIMATIONTRACK_H

#include <stdint.h>

namespace Walaber {
struct SpriteAnimationTrack {
    // size 72, align 8, confidence high
    uint64_t f_0x0;
    uint64_t f_0x8;
    uint64_t f_0x10;
    uint64_t f_0x18;
    uint64_t f_0x20;
    uint64_t f_0x28;
    uint64_t f_0x30;
    int32_t f_0x38;
    int32_t f_0x3c;
    int32_t f_0x40;
    uint8_t _tail[4];
};

}  // namespace Walaber
#endif
