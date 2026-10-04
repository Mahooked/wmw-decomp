// Recovered from WaterConcept::Screen_WorldSelect. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WATERCONCEPT__SCREEN_WORLDSELECT_H
#define WMW_WATERCONCEPT__SCREEN_WORLDSELECT_H

#include <stdint.h>

namespace WaterConcept {
struct Screen_WorldSelect {
    // size 536, align 8, confidence high
    uint64_t f_0x0;
    uint8_t _pad16[8];
    uint64_t f_0x10;
    uint8_t _pad160[136];
    int32_t f_0xa0;
    uint8_t _pad168[4];
    int32_t f_0xa8;
    int32_t f_0xac;
    uint8_t _pad179[3];
    uint8_t f_0xb3;
    uint8_t _pad240[60];
    uint64_t f_0xf0;
    uint8_t _pad336[88];
    uint64_t f_0x150;
    double f_0x158;
    uint64_t f_0x160;
    float f_0x168;
    uint8_t _pad384[20];
    int32_t f_0x180;
    uint8_t _pad448[60];
    uint64_t f_0x1c0;
    int32_t f_0x1c8;
    uint8_t f_0x1cc;
    uint8_t _pad472[11];
    int32_t f_0x1d8;
    uint8_t _pad480[4];
    int32_t f_0x1e0;
    uint8_t _pad488[4];
    int32_t f_0x1e8;
    uint8_t _pad496[4];
    int32_t f_0x1f0;
    uint8_t _pad504[4];
    int32_t f_0x1f8;
    uint8_t _pad528[20];
    uint8_t f_0x210;
    uint8_t _pad530[1];
    uint8_t f_0x212;
    uint8_t _tail[5];
};

}  // namespace WaterConcept
#endif
