// Recovered from WaterConcept::YSwitch. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WATERCONCEPT__YSWITCH_H
#define WMW_WATERCONCEPT__YSWITCH_H

#include <stdint.h>

namespace WaterConcept {
struct YSwitch {
    // size 1352, align 8, confidence high
    uint64_t f_0x0;
    uint8_t _pad400[392];
    uint64_t f_0x190;
    uint8_t _pad1216[808];
    uint64_t f_0x4c0;
    uint8_t _pad1285[61];
    uint8_t f_0x505;
    uint8_t _pad1288[2];
    int32_t f_0x508;
    int32_t f_0x50c;
    int32_t f_0x510;
    int32_t f_0x514;
    int32_t f_0x518;
    int32_t f_0x51c;
    uint64_t f_0x520;
    float f_0x528;
    uint8_t _pad1328[4];
    float f_0x530;
    float f_0x534;
    float f_0x538;
    uint8_t _pad1344[4];
    float f_0x540;
    float f_0x544;
};

}  // namespace WaterConcept
#endif
