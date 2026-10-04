// Recovered from Walaber::Transition_Slide. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WALABER__TRANSITION_SLIDE_H
#define WMW_WALABER__TRANSITION_SLIDE_H

#include <stdint.h>

namespace Walaber {
struct Transition_Slide {
    // size 296, align 8, confidence high
    uint64_t f_0x0;
    uint8_t _pad112[104];
    float f_0x70;
    float f_0x74;
    uint8_t _pad192[72];
    uint8_t f_0xc0;
    uint8_t _pad196[3];
    int32_t f_0xc4;
    int32_t f_0xc8;
    int32_t f_0xcc;
    int32_t f_0xd0;
    uint32_t f_0xd4;
    uint8_t _pad220[4];
    int32_t f_0xdc;
    uint8_t f_0xe0;
    uint8_t _pad228[3];
    uint32_t f_0xe4;
    uint8_t _pad236[4];
    float f_0xec;
    uint8_t _pad244[4];
    uint32_t f_0xf4;
    uint8_t _pad252[4];
    uint32_t f_0xfc;
    uint8_t _pad264[8];
    uint64_t f_0x108;
    uint8_t _pad280[8];
    float f_0x118;
    float f_0x11c;
    uint8_t f_0x120;
    uint8_t _pad292[3];
    int32_t f_0x124;
};

}  // namespace Walaber
#endif
