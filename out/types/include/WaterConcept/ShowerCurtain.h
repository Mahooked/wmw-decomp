// Recovered from WaterConcept::ShowerCurtain. Offsets and element types come from load/store
// evidence in the binary; the names do not, and are inferred
// from the accessor symbols noted against them. Everything else
// is named after the offset it sits at.
#ifndef WMW_WATERCONCEPT__SHOWERCURTAIN_H
#define WMW_WATERCONCEPT__SHOWERCURTAIN_H

#include <stdint.h>

namespace WaterConcept {
struct ShowerCurtain {
    // size 176, align 8, confidence high
    float f_0x0;
    uint8_t _pad8[4];
    float f_0x8;
    float f_0xc;
    int32_t f_0x10;
    int32_t lightingForVert;  // named from _getLightingForVert
    int32_t f_0x18;
    uint8_t _pad32[4];
    uint64_t f_0x20;
    uint8_t _pad120[80];
    float f_0x78;
    uint8_t _pad136[12];
    uint64_t f_0x88;
    uint8_t _pad152[8];
    int32_t f_0x98;
    uint8_t _pad160[4];
    int32_t f_0xa0;
    uint8_t _pad168[4];
    uint64_t f_0xa8;
};

}  // namespace WaterConcept
#endif
