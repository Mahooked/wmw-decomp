// Recovered from Walaber::Transition_Iris. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WALABER__TRANSITION_IRIS_H
#define WMW_WALABER__TRANSITION_IRIS_H

#include <stdint.h>

namespace Walaber {
struct Transition_Iris {
    // size 264, align 8, confidence high
    uint64_t f_0x0;
    uint8_t _pad112[104];
    float f_0x70;
    float f_0x74;
    float f_0x78;
    uint8_t f_0x7c;
    uint8_t _pad196[71];
    uint8_t f_0xc4;
    uint8_t _pad200[3];
    int32_t f_0xc8;
    float f_0xcc;
    float f_0xd0;
    uint8_t _pad220[8];
    float f_0xdc;
    uint64_t f_0xe0;
    uint64_t f_0xe8;
    uint64_t f_0xf0;
    uint64_t f_0xf8;
    uint64_t f_0x100;
};

}  // namespace Walaber
#endif
