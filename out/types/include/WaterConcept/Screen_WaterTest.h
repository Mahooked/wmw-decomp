// Recovered from WaterConcept::Screen_WaterTest. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WATERCONCEPT__SCREEN_WATERTEST_H
#define WMW_WATERCONCEPT__SCREEN_WATERTEST_H

#include <stdint.h>

namespace WaterConcept {
struct Screen_WaterTest {
    // size 680, align 8, confidence high
    uint64_t f_0x0;
    uint8_t _pad16[8];
    uint64_t f_0x10;
    uint8_t _pad168[144];
    uint64_t f_0xa8;
    uint8_t _pad438[262];
    uint8_t f_0x1b6;
    uint8_t _pad456[17];
    uint64_t f_0x1c8;
    uint8_t _pad576[112];
    uint64_t f_0x240;
    uint64_t f_0x248;
    uint64_t f_0x250;
    uint64_t f_0x258;
    uint8_t _pad614[6];
    uint8_t f_0x266;
    uint8_t f_0x267;
    uint8_t _pad652[36];
    uint8_t f_0x28c;
    uint8_t _pad656[3];
    uint64_t f_0x290;
    uint8_t _pad672[8];
    int32_t f_0x2a0;
    uint8_t _tail[4];
};

}  // namespace WaterConcept
#endif
