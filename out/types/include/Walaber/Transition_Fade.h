// Recovered from Walaber::Transition_Fade. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WALABER__TRANSITION_FADE_H
#define WMW_WALABER__TRANSITION_FADE_H

#include <stdint.h>

namespace Walaber {
struct Transition_Fade {
    // size 232, align 8, confidence high
    uint64_t f_0x0;
    uint8_t _pad112[104];
    float f_0x70;
    float f_0x74;
    int32_t f_0x78;
    uint8_t f_0x7c;
    uint8_t _pad192[67];
    uint8_t f_0xc0;
    uint8_t _pad196[3];
    uint8_t f_0xc4;
    uint8_t _pad200[3];
    int32_t f_0xc8;
    uint32_t f_0xcc;
    uint8_t _pad212[4];
    uint32_t f_0xd4;
    uint8_t _pad220[4];
    uint8_t f_0xdc;
    uint8_t _pad222[1];
    uint8_t f_0xde;
    uint8_t f_0xdf;
    uint8_t f_0xe0;
    uint8_t _pad228[3];
    uint8_t f_0xe4;
    uint8_t _pad230[1];
    uint8_t f_0xe6;
    uint8_t f_0xe7;
};

}  // namespace Walaber
#endif
