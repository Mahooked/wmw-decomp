// Recovered from WaterConcept::World. Offsets and element types come from load/store
// evidence in the binary; the names do not, and are inferred
// from the accessor symbols noted against them. Everything else
// is named after the offset it sits at.
#ifndef WMW_WATERCONCEPT__WORLD_H
#define WMW_WATERCONCEPT__WORLD_H

#include <stdint.h>

namespace WaterConcept {
struct World {
    // size 2520, align 8, confidence high
    uint64_t materialForPosition;  // named from getMaterialForPosition
    uint8_t _pad16[8];
    uint64_t f_0x10;
    uint8_t _pad1088[1064];
    uint64_t hasOrCanProduce;  // named from hasOrCanProduce
    uint8_t _pad1208[112];
    uint64_t f_0x4b8;
    uint64_t f_0x4c0;
    uint8_t _pad1448[224];
    uint64_t f_0x5a8;
    uint8_t _pad1480[24];
    uint64_t f_0x5c8;
    uint8_t _pad2512[1024];
    uint64_t f_0x9d0;
};

}  // namespace WaterConcept
#endif
