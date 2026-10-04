// Recovered from Walaber::PropertyList. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WALABER__PROPERTYLIST_H
#define WMW_WALABER__PROPERTYLIST_H

#include <stdint.h>

namespace Walaber {
struct PropertyList {
    // size 24, align 8, confidence high
    uint64_t f_0x0;
    uint64_t f_0x8;
    uint64_t f_0x10;
};

}  // namespace Walaber
#endif
