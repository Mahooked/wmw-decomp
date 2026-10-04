// Recovered from WaterConcept::AlgaeHider. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WATERCONCEPT__ALGAEHIDER_H
#define WMW_WATERCONCEPT__ALGAEHIDER_H

#include <stdint.h>

namespace WaterConcept {
struct AlgaeHider {
    // size 984, align 8, confidence high
    double f_0x0;
    uint8_t _pad936[928];
    uint64_t f_0x3a8;
    uint8_t _pad952[8];
    int32_t f_0x3b8;
    uint8_t _pad960[4];
    uint64_t f_0x3c0;
    uint8_t _pad976[8];
    uint64_t f_0x3d0;
};

}  // namespace WaterConcept
#endif
