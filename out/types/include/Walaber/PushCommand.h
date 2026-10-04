// Recovered from Walaber::PushCommand. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WALABER__PUSHCOMMAND_H
#define WMW_WALABER__PUSHCOMMAND_H

#include <stdint.h>

namespace Walaber {
struct PushCommand {
    // size 56, align 8, confidence high
    uint8_t _pad8[8];
    uint64_t f_0x8;
    uint8_t _pad32[16];
    uint64_t f_0x20;
    uint8_t _pad48[8];
    int32_t f_0x30;
    uint8_t f_0x34;
    uint8_t _tail[3];
};

}  // namespace Walaber
#endif
