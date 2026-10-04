// Recovered from Walaber::SkeletonActorCueAnimationTrack. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WALABER__SKELETONACTORCUEANIMATIONTRACK_H
#define WMW_WALABER__SKELETONACTORCUEANIMATIONTRACK_H

#include <stdint.h>

namespace Walaber {
struct SkeletonActorCueAnimationTrack {
    // size 40, align 8, confidence high
    uint64_t f_0x0;
    uint64_t f_0x8;
    uint64_t f_0x10;
    uint8_t _pad32[8];
    uint64_t f_0x20;
};

}  // namespace Walaber
#endif
