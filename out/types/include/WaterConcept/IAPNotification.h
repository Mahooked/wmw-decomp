// Recovered from WaterConcept::IAPNotification. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WATERCONCEPT__IAPNOTIFICATION_H
#define WMW_WATERCONCEPT__IAPNOTIFICATION_H

#include <stdint.h>

namespace WaterConcept {
struct IAPNotification {
    // size 632, align 8, confidence high
    uint16_t f_0x0;
    uint8_t _pad448[446];
    int32_t f_0x1c0;
    uint8_t _pad488[36];
    uint64_t f_0x1e8;
    uint8_t _pad508[12];
    uint8_t f_0x1fc;
    uint8_t _pad512[3];
    uint64_t f_0x200;
    uint64_t f_0x208;
    uint8_t f_0x210;
    uint8_t _pad536[7];
    uint64_t f_0x218;
    uint64_t f_0x220;
    double f_0x228;
    int32_t f_0x230;
    uint8_t _pad576[12];
    uint64_t f_0x240;
    uint8_t f_0x248;
    uint8_t _pad592[7];
    uint64_t f_0x250;
    uint64_t f_0x258;
    uint8_t f_0x260;
    uint8_t _pad624[15];
    uint64_t f_0x270;
};

}  // namespace WaterConcept
#endif
