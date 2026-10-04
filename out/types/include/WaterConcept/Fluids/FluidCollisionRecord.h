// Recovered from WaterConcept::Fluids::FluidCollisionRecord. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WATERCONCEPT__FLUIDS__FLUIDCOLLISIONRECORD_H
#define WMW_WATERCONCEPT__FLUIDS__FLUIDCOLLISIONRECORD_H

#include <stdint.h>

namespace WaterConcept {
namespace Fluids {
struct FluidCollisionRecord {
    // size 32, align 16, confidence high
    uint64_t f_0x0;
    uint8_t _pad16[8];
    uint64_t f_0x10;
    uint64_t f_0x18;
};

}  // namespace WaterConcept::Fluids
#endif
