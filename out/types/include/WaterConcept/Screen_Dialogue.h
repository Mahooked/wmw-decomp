// Recovered from WaterConcept::Screen_Dialogue. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WATERCONCEPT__SCREEN_DIALOGUE_H
#define WMW_WATERCONCEPT__SCREEN_DIALOGUE_H

#include <stdint.h>

namespace WaterConcept {
struct Screen_Dialogue {
    // size 400, align 8, confidence high
    uint8_t f_0x0;
    uint8_t _pad16[15];
    uint64_t f_0x10;
    uint8_t _pad32[8];
    uint64_t f_0x20;
    uint8_t _pad144[104];
    uint8_t f_0x90;
    uint8_t _pad148[3];
    int32_t f_0x94;
    int32_t f_0x98;
    uint8_t _pad160[4];
    uint64_t f_0xa0;
    uint64_t f_0xa8;
    uint64_t f_0xb0;
    int32_t f_0xb8;
    uint8_t _pad192[4];
    int32_t f_0xc0;
    uint8_t f_0xc4;
    uint8_t f_0xc5;
    uint8_t _pad200[2];
    int32_t f_0xc8;
    int32_t f_0xcc;
    int32_t f_0xd0;
    int32_t f_0xd4;
    uint64_t f_0xd8;
    uint64_t f_0xe0;
    uint8_t _pad244[12];
    float f_0xf4;
    uint8_t _pad252[4];
    uint32_t f_0xfc;
    uint8_t _pad320[64];
    uint8_t f_0x140;
    uint8_t _pad328[7];
    uint64_t f_0x148;
    uint64_t f_0x150;
    uint8_t f_0x158;
    uint8_t _pad352[7];
    uint64_t f_0x160;
    uint64_t f_0x168;
    uint8_t f_0x170;
    uint8_t _pad376[7];
    uint64_t f_0x178;
    uint64_t f_0x180;
    uint8_t f_0x188;
    uint8_t f_0x189;
    uint8_t _pad395[1];
    uint8_t f_0x18b;
    float f_0x18c;
};

}  // namespace WaterConcept
#endif
