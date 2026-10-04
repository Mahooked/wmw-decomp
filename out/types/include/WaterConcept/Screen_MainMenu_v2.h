// Recovered from WaterConcept::Screen_MainMenu_v2. Offsets and element types come from load/store
// evidence in the binary; the names do not, and are inferred
// from the accessor symbols noted against them. Everything else
// is named after the offset it sits at.
#ifndef WMW_WATERCONCEPT__SCREEN_MAINMENU_V2_H
#define WMW_WATERCONCEPT__SCREEN_MAINMENU_V2_H

#include <stdint.h>

namespace WaterConcept {
struct Screen_MainMenu_v2 {
    // size 1080, align 8, confidence high
    uint64_t f_0x0;
    uint8_t _pad16[8];
    uint64_t f_0x10;
    uint8_t _pad160[136];
    uint64_t f_0xa0;
    uint8_t _pad176[8];
    uint8_t f_0xb0;
    uint8_t _pad180[3];
    int32_t f_0xb4;
    uint8_t _pad224[40];
    uint8_t subscreenIDForCurrentIndex;  // named from _getSubscreenIDForCurrentIndex
    uint8_t _pad440[215];
    uint64_t f_0x1b8;
    uint8_t _pad520[72];
    uint64_t f_0x208;
    uint64_t f_0x210;
    uint8_t _pad680[144];
    int32_t f_0x2a8;
    uint8_t _pad936[252];
    uint64_t f_0x3a8;
    uint8_t _pad952[8];
    uint64_t f_0x3b8;
    uint64_t f_0x3c0;
    uint8_t _pad1036[68];
    uint8_t f_0x40c;
    uint8_t _pad1038[1];
    uint8_t f_0x40e;
    uint8_t _pad1072[33];
    uint64_t f_0x430;
};

}  // namespace WaterConcept
#endif
