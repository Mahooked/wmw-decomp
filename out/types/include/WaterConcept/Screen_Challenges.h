// Recovered from WaterConcept::Screen_Challenges. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WATERCONCEPT__SCREEN_CHALLENGES_H
#define WMW_WATERCONCEPT__SCREEN_CHALLENGES_H

#include <stdint.h>

namespace WaterConcept {
struct Screen_Challenges {
    // size 232, align 8, confidence high
    uint64_t f_0x0;
    uint8_t _pad16[8];
    uint64_t f_0x10;
    uint8_t _pad32[8];
    uint64_t f_0x20;
    uint8_t _pad144[104];
    uint64_t f_0x90;
    uint8_t _pad160[8];
    uint8_t f_0xa0;
    uint8_t _pad176[15];
    uint64_t f_0xb0;
    uint8_t _pad188[4];
    float f_0xbc;
    uint8_t _pad200[8];
    uint64_t f_0xc8;
    uint8_t _pad224[16];
    uint64_t f_0xe0;
};

}  // namespace WaterConcept
#endif
