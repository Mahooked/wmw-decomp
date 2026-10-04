// Recovered from Walaber::CompressionRecord. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WALABER__COMPRESSIONRECORD_H
#define WMW_WALABER__COMPRESSIONRECORD_H

#include <stdint.h>

namespace Walaber {
struct CompressionRecord {
    // size 8, align 4, confidence high
    float f_0x0;
    float f_0x4;
};

}  // namespace Walaber
#endif
