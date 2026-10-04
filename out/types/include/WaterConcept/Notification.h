// Recovered from WaterConcept::Notification. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WATERCONCEPT__NOTIFICATION_H
#define WMW_WATERCONCEPT__NOTIFICATION_H

#include <stdint.h>

namespace WaterConcept {
struct Notification {
    // size 480, align 8, confidence high
    uint64_t f_0x0;
    uint64_t f_0x8;
    uint8_t _pad152[136];
    uint64_t f_0x98;
    uint8_t _pad288[128];
    int32_t f_0x120;
    uint8_t _pad416[124];
    int32_t f_0x1a0;
    uint8_t _pad424[4];
    float f_0x1a8;
    uint8_t _pad432[4];
    float f_0x1b0;
    uint8_t _pad440[4];
    float f_0x1b8;
    float f_0x1bc;
    int32_t f_0x1c0;
    uint8_t _pad456[4];
    uint8_t f_0x1c8;
    uint8_t _pad472[15];
    uint64_t f_0x1d8;
};

}  // namespace WaterConcept
#endif
