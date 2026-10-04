// Recovered from WaterConcept::DirtyWall. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WATERCONCEPT__DIRTYWALL_H
#define WMW_WATERCONCEPT__DIRTYWALL_H

#include <stdint.h>

namespace WaterConcept {
struct DirtyWall {
    // size 1008, align 8, confidence high
    float f_0x0;
    uint8_t _pad936[932];
    uint64_t f_0x3a8;
    uint64_t f_0x3b0;
    uint8_t _pad960[8];
    uint8_t f_0x3c0;
    uint8_t _pad984[23];
    uint64_t f_0x3d8;
    uint64_t f_0x3e0;
    uint64_t f_0x3e8;
};

}  // namespace WaterConcept
#endif
