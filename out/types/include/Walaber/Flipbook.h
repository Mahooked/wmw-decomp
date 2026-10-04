// Recovered from Walaber::Flipbook. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WALABER__FLIPBOOK_H
#define WMW_WALABER__FLIPBOOK_H

#include <stdint.h>

namespace Walaber {
struct Flipbook {
    // size 32, align 8, confidence high
    uint8_t _pad16[16];
    uint64_t f_0x10;
    uint64_t f_0x18;
};

}  // namespace Walaber
#endif
