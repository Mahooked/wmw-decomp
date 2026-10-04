// Recovered from Walaber::FingerInfo. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WALABER__FINGERINFO_H
#define WMW_WALABER__FINGERINFO_H

#include <stdint.h>

namespace Walaber {
struct FingerInfo {
    // size 12, align 4, confidence high
    uint8_t _pad4[4];
    uint32_t f_0x4;
    uint8_t _tail[4];
};

}  // namespace Walaber
#endif
