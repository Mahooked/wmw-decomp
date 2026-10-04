// Recovered from WaterConcept::PurchaseHandler. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WATERCONCEPT__PURCHASEHANDLER_H
#define WMW_WATERCONCEPT__PURCHASEHANDLER_H

#include <stdint.h>

namespace WaterConcept {
struct PurchaseHandler {
    // size 40, align 8, confidence high
    uint64_t f_0x0;
    uint8_t _pad16[8];
    uint8_t f_0x10;
    uint8_t _pad32[15];
    uint64_t f_0x20;
};

}  // namespace WaterConcept
#endif
