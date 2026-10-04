// Recovered from Walaber::Node. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WALABER__NODE_H
#define WMW_WALABER__NODE_H

#include <stdint.h>

namespace Walaber {
struct Node {
    // size 128, align 8, confidence high
    uint8_t _pad8[8];
    uint64_t f_0x8;
    uint64_t f_0x10;
    uint64_t f_0x18;
    int32_t f_0x20;
    uint8_t _pad84[48];
    int32_t f_0x54;
    int32_t f_0x58;
    int32_t f_0x5c;
    int32_t f_0x60;
    int32_t f_0x64;
    int32_t f_0x68;
    int32_t f_0x6c;
    uint8_t _pad116[4];
    float f_0x74;
    uint8_t _pad124[4];
    uint8_t f_0x7c;
    uint8_t f_0x7d;
    uint8_t f_0x7e;
    uint8_t _tail[1];
};

}  // namespace Walaber
#endif
