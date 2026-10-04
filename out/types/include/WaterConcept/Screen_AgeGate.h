// Recovered from WaterConcept::Screen_AgeGate. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WATERCONCEPT__SCREEN_AGEGATE_H
#define WMW_WATERCONCEPT__SCREEN_AGEGATE_H

#include <stdint.h>

namespace WaterConcept {
struct Screen_AgeGate {
    // size 264, align 8, confidence high
    uint64_t f_0x0;
    uint8_t _pad16[8];
    uint64_t f_0x10;
    uint8_t _pad32[8];
    uint64_t f_0x20;
    uint8_t _pad144[104];
    uint64_t f_0x90;
    uint8_t _pad160[8];
    uint64_t f_0xa0;
    uint8_t _pad176[8];
    uint64_t f_0xb0;
    uint8_t _pad192[8];
    uint8_t f_0xc0;
    uint8_t _pad196[3];
    float f_0xc4;
    uint8_t f_0xc8;
    uint8_t f_0xc9;
    uint8_t _pad204[2];
    int32_t f_0xcc;
    uint8_t _pad240[32];
    uint64_t f_0xf0;
    float f_0xf8;
    int32_t f_0xfc;
    uint8_t f_0x100;
    uint8_t f_0x101;
    uint8_t _tail[6];
};

}  // namespace WaterConcept
#endif
