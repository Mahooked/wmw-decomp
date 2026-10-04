// Recovered from WaterConcept::MysteryCave. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WATERCONCEPT__MYSTERYCAVE_H
#define WMW_WATERCONCEPT__MYSTERYCAVE_H

#include <stdint.h>

namespace WaterConcept {
struct MysteryCave {
    // size 976, align 8, confidence high
    uint64_t f_0x0;
    uint8_t _pad184[176];
    uint64_t f_0xb8;
    uint8_t _pad936[744];
    uint64_t f_0x3a8;
    uint8_t _pad952[8];
    uint8_t f_0x3b8;
    uint8_t _pad956[3];
    float f_0x3bc;
    int32_t f_0x3c0;
    uint8_t _pad968[4];
    uint8_t f_0x3c8;
    uint8_t _pad972[3];
    int32_t f_0x3cc;
};

}  // namespace WaterConcept
#endif
