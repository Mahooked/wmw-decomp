// Recovered from Walaber::Transition_Block. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WALABER__TRANSITION_BLOCK_H
#define WMW_WALABER__TRANSITION_BLOCK_H

#include <stdint.h>

namespace Walaber {
struct Transition_Block {
    // size 264, align 8, confidence high
    uint64_t f_0x0;
    uint8_t _pad112[104];
    float f_0x70;
    float f_0x74;
    int32_t f_0x78;
    uint8_t _pad196[72];
    uint8_t f_0xc4;
    uint8_t _pad200[3];
    int32_t f_0xc8;
    uint32_t f_0xcc;
    uint8_t _pad212[4];
    float f_0xd4;
    uint8_t _pad224[8];
    uint64_t f_0xe0;
    uint64_t f_0xe8;
    uint8_t _pad248[8];
    int32_t f_0xf8;
    int32_t f_0xfc;
    int32_t f_0x100;
    int32_t f_0x104;
};

}  // namespace Walaber
#endif
