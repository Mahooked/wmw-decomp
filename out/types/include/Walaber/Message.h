// Recovered from Walaber::Message. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WALABER__MESSAGE_H
#define WMW_WALABER__MESSAGE_H

#include <stdint.h>

namespace Walaber {
struct Message {
    // size 16, align 4, confidence high
    uint8_t _pad12[12];
    int32_t f_0xc;
};

}  // namespace Walaber
#endif
