// Recovered from Walaber::AnimationManager. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WALABER__ANIMATIONMANAGER_H
#define WMW_WALABER__ANIMATIONMANAGER_H

#include <stdint.h>

namespace Walaber {
struct AnimationManager {
    // size 80, align 8, confidence high
    uint64_t f_0x0;
    uint8_t _pad24[16];
    uint64_t f_0x18;
    uint64_t f_0x20;
    uint8_t _pad56[16];
    uint64_t f_0x38;
    float f_0x40;
    uint8_t _pad72[4];
    uint8_t f_0x48;
    uint8_t _tail[7];
};

}  // namespace Walaber
#endif
