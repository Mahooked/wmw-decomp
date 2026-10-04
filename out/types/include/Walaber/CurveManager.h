// Recovered from Walaber::CurveManager. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WALABER__CURVEMANAGER_H
#define WMW_WALABER__CURVEMANAGER_H

#include <stdint.h>

namespace Walaber {
struct CurveManager {
    // size 136, align 8, confidence high
    uint8_t _pad16[16];
    uint64_t f_0x10;
    uint64_t f_0x18;
    uint8_t _pad40[8];
    uint64_t f_0x28;
    uint64_t f_0x30;
    uint64_t f_0x38;
    uint64_t f_0x40;
    uint8_t _pad80[8];
    uint64_t f_0x50;
    uint8_t _pad104[16];
    uint64_t f_0x68;
    uint8_t _pad120[8];
    uint64_t f_0x78;
    uint64_t f_0x80;
};

}  // namespace Walaber
#endif
