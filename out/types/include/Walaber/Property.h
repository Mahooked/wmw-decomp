// Recovered from Walaber::Property. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WALABER__PROPERTY_H
#define WMW_WALABER__PROPERTY_H

#include <stdint.h>

namespace Walaber {
struct Property {
    // size 40, align 8, confidence high
    int32_t f_0x0;
    uint8_t _pad8[4];
    uint8_t f_0x8;
    uint8_t _pad24[15];
    uint64_t f_0x18;
    uint64_t f_0x20;
};

}  // namespace Walaber
#endif
