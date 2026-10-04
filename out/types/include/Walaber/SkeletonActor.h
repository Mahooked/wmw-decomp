// Recovered from Walaber::SkeletonActor. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WALABER__SKELETONACTOR_H
#define WMW_WALABER__SKELETONACTOR_H

#include <stdint.h>

namespace Walaber {
struct SkeletonActor {
    // size 392, align 8, confidence high
    uint8_t _pad8[8];
    uint64_t f_0x8;
    uint64_t f_0x10;
    uint8_t _pad40[16];
    uint64_t f_0x28;
    uint8_t _pad64[16];
    uint64_t f_0x40;
    uint64_t f_0x48;
    uint8_t _pad124[44];
    int32_t f_0x7c;
    uint8_t _pad152[24];
    uint64_t f_0x98;
    uint64_t f_0xa0;
    uint8_t _pad176[8];
    uint64_t f_0xb0;
    uint64_t f_0xb8;
    uint8_t _pad328[136];
    uint64_t f_0x148;
    uint8_t _pad376[40];
    uint64_t f_0x178;
    uint64_t f_0x180;
};

}  // namespace Walaber
#endif
