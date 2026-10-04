// Recovered from Walaber::PCSNode. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WALABER__PCSNODE_H
#define WMW_WALABER__PCSNODE_H

#include <stdint.h>

namespace Walaber {
struct PCSNode {
    // size 32, align 8, confidence high
    uint8_t f_0x0;
    uint8_t _pad8[7];
    uint64_t f_0x8;
    uint64_t f_0x10;
    uint64_t f_0x18;
};

}  // namespace Walaber
#endif
