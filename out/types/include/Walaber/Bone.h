// Recovered from Walaber::Bone. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WALABER__BONE_H
#define WMW_WALABER__BONE_H

#include <stdint.h>

namespace Walaber {
struct Bone {
    // size 120, align 8, confidence med
    uint8_t _pad8[8];
    uint64_t f_0x8;
    uint64_t f_0x10;
    uint64_t f_0x18;
    uint8_t _pad84[52];
    uint32_t f_0x54;
    uint8_t _pad92[4];
    uint32_t f_0x5c;
    uint8_t _pad116[20];
    int32_t f_0x74;
};

}  // namespace Walaber
#endif
