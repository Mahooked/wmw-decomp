// Recovered from WaterConcept::Screen_MysteryShow. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WATERCONCEPT__SCREEN_MYSTERYSHOW_H
#define WMW_WATERCONCEPT__SCREEN_MYSTERYSHOW_H

#include <stdint.h>

namespace WaterConcept {
struct Screen_MysteryShow {
    // size 216, align 8, confidence high
    uint64_t f_0x0;
    uint8_t _pad16[8];
    uint64_t f_0x10;
    uint8_t _pad32[8];
    uint64_t f_0x20;
    uint8_t _pad144[104];
    uint64_t f_0x90;
    int32_t f_0x98;
    float f_0x9c;
    int32_t f_0xa0;
    int32_t f_0xa4;
    uint64_t f_0xa8;
    uint64_t f_0xb0;
    uint64_t f_0xb8;
    uint64_t f_0xc0;
    uint8_t _pad208[8];
    float f_0xd0;
    uint8_t f_0xd4;
    uint8_t _tail[3];
};

}  // namespace WaterConcept
#endif
