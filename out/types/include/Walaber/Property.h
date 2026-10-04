// Recovered from Walaber::Property. Offsets and element types come from load/store
// evidence in the binary; the names do not, and are inferred
// from the accessor symbols noted against them. Everything else
// is named after the offset it sits at.
#ifndef WMW_WALABER__PROPERTY_H
#define WMW_WALABER__PROPERTY_H

#include <stdint.h>

namespace Walaber {
struct Property {
    // size 40, align 8, confidence high
    int32_t value;  // named from setValue
    uint8_t _pad8[4];
    uint8_t f_0x8;
    uint8_t _pad24[15];
    uint64_t f_0x18;
    uint64_t f_0x20;
};

}  // namespace Walaber
#endif
