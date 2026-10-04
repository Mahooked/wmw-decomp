// Recovered from WaterConcept::Screen_Languages. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WATERCONCEPT__SCREEN_LANGUAGES_H
#define WMW_WATERCONCEPT__SCREEN_LANGUAGES_H

#include <stdint.h>

namespace WaterConcept {
struct Screen_Languages {
    // size 216, align 8, confidence high
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
    uint8_t _pad192[16];
    int32_t f_0xc0;
    int32_t f_0xc4;
    int32_t f_0xc8;
    int32_t f_0xcc;
    uint8_t f_0xd0;
    uint8_t _pad212[3];
    int32_t f_0xd4;
};

}  // namespace WaterConcept
#endif
