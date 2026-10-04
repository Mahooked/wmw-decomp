// Recovered from WaterConcept::SeaweedStrand. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WATERCONCEPT__SEAWEEDSTRAND_H
#define WMW_WATERCONCEPT__SEAWEEDSTRAND_H

#include <stdint.h>

namespace WaterConcept {
struct SeaweedStrand {
    // size 176, align 8, confidence high
    float f_0x0;
    int32_t f_0x4;
    float f_0x8;
    uint8_t _pad16[4];
    float f_0x10;
    uint32_t f_0x14;
    uint8_t _pad32[8];
    uint64_t f_0x20;
    uint8_t _pad120[80];
    float f_0x78;
    uint8_t _pad136[12];
    uint64_t f_0x88;
    uint8_t _pad152[8];
    int32_t f_0x98;
    uint8_t _pad160[4];
    int32_t f_0xa0;
    int32_t f_0xa4;
    uint64_t f_0xa8;
};

}  // namespace WaterConcept
#endif
