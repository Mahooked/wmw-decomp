// Recovered from Walaber::Transition. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WALABER__TRANSITION_H
#define WMW_WALABER__TRANSITION_H

#include <stdint.h>

namespace Walaber {
struct Transition {
    // size 200, align 8, confidence high
    uint64_t f_0x0;
    uint8_t _pad128[120];
    uint8_t f_0x80;
    uint8_t _pad136[7];
    uint8_t f_0x88;
    uint8_t _pad138[1];
    uint8_t f_0x8a;
    uint8_t _pad144[5];
    uint64_t f_0x90;
    uint8_t f_0x98;
    uint8_t _pad160[7];
    uint64_t f_0xa0;
    uint64_t f_0xa8;
    double f_0xb0;
    float f_0xb8;
    int32_t f_0xbc;
    int32_t f_0xc0;
    uint8_t _tail[4];
};

}  // namespace Walaber
#endif
