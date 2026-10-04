// Recovered from Walaber::CharacterManager. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WALABER__CHARACTERMANAGER_H
#define WMW_WALABER__CHARACTERMANAGER_H

#include <stdint.h>

namespace Walaber {
struct CharacterManager {
    // size 16, align 8, confidence high
    uint8_t _pad8[8];
    uint64_t f_0x8;
};

}  // namespace Walaber
#endif
