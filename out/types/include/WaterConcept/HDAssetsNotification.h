// Recovered from WaterConcept::HDAssetsNotification. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WATERCONCEPT__HDASSETSNOTIFICATION_H
#define WMW_WATERCONCEPT__HDASSETSNOTIFICATION_H

#include <stdint.h>

namespace WaterConcept {
struct HDAssetsNotification {
    // size 520, align 8, confidence high
    uint64_t f_0x0;
    uint8_t _pad500[492];
    uint8_t f_0x1f4;
    uint8_t f_0x1f5;
    uint8_t f_0x1f6;
    uint8_t f_0x1f7;
    uint8_t f_0x1f8;
    uint8_t f_0x1f9;
    uint8_t f_0x1fa;
    uint8_t f_0x1fb;
    int32_t f_0x1fc;
    uint8_t _pad516[4];
    uint8_t f_0x204;
    uint8_t f_0x205;
    uint8_t _tail[2];
};

}  // namespace WaterConcept
#endif
