// Recovered from WaterConcept::Screen_Achievements. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WATERCONCEPT__SCREEN_ACHIEVEMENTS_H
#define WMW_WATERCONCEPT__SCREEN_ACHIEVEMENTS_H

#include <stdint.h>

namespace WaterConcept {
struct Screen_Achievements {
    // size 264, align 8, confidence high
    float f_0x0;
    uint8_t _pad16[12];
    uint64_t f_0x10;
    uint8_t _pad32[8];
    uint64_t f_0x20;
    uint8_t _pad144[104];
    uint64_t f_0x90;
    uint8_t _pad260[108];
    float f_0x104;
};

}  // namespace WaterConcept
#endif
