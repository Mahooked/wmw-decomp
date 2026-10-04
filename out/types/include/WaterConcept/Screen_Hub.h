// Recovered from WaterConcept::Screen_Hub. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WATERCONCEPT__SCREEN_HUB_H
#define WMW_WATERCONCEPT__SCREEN_HUB_H

#include <stdint.h>

namespace WaterConcept {
struct Screen_Hub {
    // size 272, align 8, confidence high
    uint64_t f_0x0;
    uint8_t _pad16[8];
    uint64_t f_0x10;
    uint8_t _pad32[8];
    uint64_t f_0x20;
    uint8_t _pad144[104];
    uint64_t f_0x90;
    uint8_t _pad172[20];
    int32_t f_0xac;
    uint8_t _pad184[8];
    uint64_t f_0xb8;
    uint8_t _pad200[8];
    uint64_t f_0xc8;
    uint64_t f_0xd0;
    uint8_t f_0xd8;
    uint8_t f_0xd9;
    uint8_t f_0xda;
    uint8_t _pad220[1];
    int32_t f_0xdc;
    uint8_t _pad232[8];
    uint64_t f_0xe8;
    uint8_t _pad248[8];
    float f_0xf8;
    uint8_t _pad264[12];
    uint64_t f_0x108;
};

}  // namespace WaterConcept
#endif
