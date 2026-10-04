// Recovered from WaterConcept::World. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WATERCONCEPT__WORLD_H
#define WMW_WATERCONCEPT__WORLD_H

#include <stdint.h>

namespace WaterConcept {
struct World {
    // size 2520, align 8, confidence high
    uint64_t f_0x0;
    uint8_t _pad16[8];
    uint64_t f_0x10;
    uint8_t _pad1088[1064];
    uint64_t f_0x440;
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
