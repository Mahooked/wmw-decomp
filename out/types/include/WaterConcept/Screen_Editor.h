// Recovered from WaterConcept::Screen_Editor. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WATERCONCEPT__SCREEN_EDITOR_H
#define WMW_WATERCONCEPT__SCREEN_EDITOR_H

#include <stdint.h>

namespace WaterConcept {
struct Screen_Editor {
    // size 536, align 8, confidence high
    uint64_t f_0x0;
    uint8_t _pad16[8];
    uint64_t f_0x10;
    uint8_t _pad152[128];
    uint64_t f_0x98;
    float f_0xa0;
    float f_0xa4;
    float f_0xa8;
    float f_0xac;
    uint8_t _pad256[80];
    uint64_t f_0x100;
    uint64_t f_0x108;
    uint8_t _pad385[113];
    uint8_t f_0x181;
    uint8_t _pad392[6];
    uint64_t f_0x188;
    uint64_t f_0x190;
    uint8_t _pad416[8];
    uint64_t f_0x1a0;
    uint8_t _pad432[8];
    uint64_t f_0x1b0;
    uint8_t _pad520[80];
    uint64_t f_0x208;
    uint64_t f_0x210;
};

}  // namespace WaterConcept
#endif
