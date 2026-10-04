// Recovered from Walaber::PlatformManager. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WALABER__PLATFORMMANAGER_H
#define WMW_WALABER__PLATFORMMANAGER_H

#include <stdint.h>

namespace Walaber {
struct PlatformManager {
    // size 56, align 4, confidence high
    uint8_t _pad48[48];
    int32_t f_0x30;
    int32_t f_0x34;
};

}  // namespace Walaber
#endif
