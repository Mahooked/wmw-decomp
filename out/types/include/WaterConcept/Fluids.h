// Recovered from WaterConcept::Fluids. Offsets and element types come from load/store
// evidence in the binary; the names do not, and are inferred
// from the accessor symbols noted against them. Everything else
// is named after the offset it sits at.
#ifndef WMW_WATERCONCEPT__FLUIDS_H
#define WMW_WATERCONCEPT__FLUIDS_H

#include <stdint.h>

namespace WaterConcept {
struct Fluids {
    // size 4, align 4, confidence high
    float particlesForFluid;  // indexed, stride 1  // named from getParticlesForFluid
};

}  // namespace WaterConcept
#endif
