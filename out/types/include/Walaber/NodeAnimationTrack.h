// Recovered from Walaber::NodeAnimationTrack. Offsets and element types come from load/store
// evidence in the binary; the names do not, and are inferred
// from the accessor symbols noted against them. Everything else
// is named after the offset it sits at.
#ifndef WMW_WALABER__NODEANIMATIONTRACK_H
#define WMW_WALABER__NODEANIMATIONTRACK_H

#include <stdint.h>

namespace Walaber {
struct NodeAnimationTrack {
    // size 104, align 8, confidence high
    int32_t f_0x0;
    float f_0x4;
    uint64_t f_0x8;
    uint8_t _pad24[8];
    uint64_t f_0x18;
    uint8_t _pad40[8];
    uint64_t f_0x28;
    uint8_t _pad56[8];
    uint64_t f_0x38;
    uint8_t _pad72[8];
    uint64_t f_0x48;
    uint8_t _pad88[8];
    uint64_t animation;  // named from setAnimation
    uint64_t f_0x60;
};

}  // namespace Walaber
#endif
