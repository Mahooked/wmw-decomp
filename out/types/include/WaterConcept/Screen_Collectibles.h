// Recovered from WaterConcept::Screen_Collectibles. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WATERCONCEPT__SCREEN_COLLECTIBLES_H
#define WMW_WATERCONCEPT__SCREEN_COLLECTIBLES_H

#include <stdint.h>

namespace WaterConcept {
struct Screen_Collectibles {
    // size 408, align 8, confidence high
    uint64_t f_0x0;
    uint8_t _pad16[8];
    uint64_t f_0x10;
    uint8_t _pad32[8];
    uint64_t f_0x20;
    uint8_t _pad144[104];
    uint64_t f_0x90;
    uint8_t _pad160[8];
    uint64_t f_0xa0;
    uint8_t _pad236[68];
    int32_t f_0xec;
    uint8_t _pad248[8];
    uint64_t f_0xf8;
    uint8_t _pad272[16];
    float f_0x110;
    uint8_t _pad288[12];
    uint64_t f_0x120;
    uint8_t _pad304[8];
    int32_t f_0x130;
    uint8_t f_0x134;
    uint8_t _pad312[3];
    uint64_t f_0x138;
    uint64_t f_0x140;
    uint64_t f_0x148;
    uint64_t f_0x150;
    uint64_t f_0x158;
    uint64_t f_0x160;
    float f_0x168;
    uint8_t _pad368[4];
    uint64_t f_0x170;
    uint8_t _pad384[8];
    uint64_t f_0x180;
    uint64_t f_0x188;
    float f_0x190;
    uint8_t _tail[4];
};

}  // namespace WaterConcept
#endif
