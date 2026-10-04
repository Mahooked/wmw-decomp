// Recovered from WaterConcept::Collectible. Offsets and element types come from load/store
// evidence in the binary; the names do not, and are inferred
// from the accessor symbols noted against them. Everything else
// is named after the offset it sits at.
#ifndef WMW_WATERCONCEPT__COLLECTIBLE_H
#define WMW_WATERCONCEPT__COLLECTIBLE_H

#include <stdint.h>

namespace WaterConcept {
struct Collectible {
    // size 1008, align 8, confidence high
    uint64_t f_0x0;
    uint8_t _pad376[368];
    uint64_t spriteWorldSize;  // named from getSpriteWorldSize
    uint64_t f_0x180;
    uint8_t _pad936[544];
    int32_t f_0x3a8;
    float f_0x3ac;
    uint64_t f_0x3b0;
    uint64_t f_0x3b8;
    float f_0x3c0;
    uint8_t f_0x3c4;
    uint8_t _pad984[19];
    float f_0x3d8;
    uint8_t _pad992[4];
    uint8_t f_0x3e0;
    uint8_t _pad996[3];
    int32_t f_0x3e4;
    uint8_t f_0x3e8;
    uint8_t isGhost;  // named from isGhost
    uint8_t _pad1004[2];
    float f_0x3ec;
};

}  // namespace WaterConcept
#endif
