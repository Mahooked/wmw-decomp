// Recovered from WaterConcept::Screen_Credits. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WATERCONCEPT__SCREEN_CREDITS_H
#define WMW_WATERCONCEPT__SCREEN_CREDITS_H

#include <stdint.h>

namespace WaterConcept {
struct Screen_Credits {
    // size 288, align 8, confidence high
    uint64_t f_0x0;
    uint8_t _pad16[8];
    uint64_t f_0x10;
    uint8_t _pad32[8];
    uint64_t f_0x20;
    uint8_t _pad144[104];
    uint64_t f_0x90;
    uint8_t _pad160[8];
    uint64_t f_0xa0;
    uint64_t f_0xa8;
    uint64_t f_0xb0;
    uint64_t f_0xb8;
    uint8_t f_0xc0;
    uint8_t _pad196[3];
    int32_t f_0xc4;
    uint64_t f_0xc8;
    uint64_t f_0xd0;
    float f_0xd8;
    uint8_t _pad224[4];
    uint8_t f_0xe0;
    uint8_t _pad226[1];
    uint8_t f_0xe2;
    uint8_t _pad228[1];
    float f_0xe4;
    float f_0xe8;
    int32_t f_0xec;
    uint8_t _pad244[4];
    uint32_t f_0xf4;
    uint8_t _pad264[16];
    uint64_t f_0x108;
    uint8_t _pad280[8];
    float f_0x118;
    uint8_t _tail[4];
};

}  // namespace WaterConcept
#endif
