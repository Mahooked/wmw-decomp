// Recovered from WaterConcept::Screen_MusicCollection. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WATERCONCEPT__SCREEN_MUSICCOLLECTION_H
#define WMW_WATERCONCEPT__SCREEN_MUSICCOLLECTION_H

#include <stdint.h>

namespace WaterConcept {
struct Screen_MusicCollection {
    // size 256, align 8, confidence high
    double f_0x0;
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
    uint64_t f_0xc0;
    uint8_t _pad208[8];
    uint8_t f_0xd0;
    uint8_t f_0xd1;
    uint8_t _pad224[14];
    uint64_t f_0xe0;
    uint8_t _pad240[8];
    int32_t f_0xf0;
    float f_0xf4;
    uint64_t f_0xf8;
};

}  // namespace WaterConcept
#endif
