// Recovered from Walaber::Transition_Wipe. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WALABER__TRANSITION_WIPE_H
#define WMW_WALABER__TRANSITION_WIPE_H

#include <stdint.h>

namespace Walaber {
struct Transition_Wipe {
    // size 248, align 8, confidence high
    uint8_t f_0x0;
    uint8_t _pad112[111];
    float f_0x70;
    float f_0x74;
    int32_t f_0x78;
    uint8_t _pad196[72];
    uint8_t f_0xc4;
    uint8_t _pad200[3];
    double f_0xc8;
    double f_0xd0;
    float f_0xd8;
    uint8_t _pad224[4];
    uint64_t f_0xe0;
    int32_t f_0xe8;
    int32_t f_0xec;
    uint8_t _pad244[4];
    int32_t f_0xf4;
};

}  // namespace Walaber
#endif
