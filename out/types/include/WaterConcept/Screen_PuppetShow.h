// Recovered from WaterConcept::Screen_PuppetShow. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WATERCONCEPT__SCREEN_PUPPETSHOW_H
#define WMW_WATERCONCEPT__SCREEN_PUPPETSHOW_H

#include <stdint.h>

namespace WaterConcept {
struct Screen_PuppetShow {
    // size 880, align 8, confidence high
    uint64_t f_0x0;
    uint8_t _pad16[8];
    uint64_t f_0x10;
    uint8_t _pad32[8];
    uint64_t f_0x20;
    uint8_t _pad784[744];
    float f_0x310;
    uint8_t f_0x314;
    uint8_t _pad792[3];
    int32_t f_0x318;
    int32_t f_0x31c;
    uint8_t _pad824[24];
    int32_t f_0x338;
    uint8_t _pad832[4];
    uint64_t f_0x340;
    uint8_t _pad848[8];
    uint8_t f_0x350;
    uint8_t _pad856[7];
    uint64_t f_0x358;
    uint64_t f_0x360;
    float f_0x368;
    uint8_t f_0x36c;
    uint8_t _tail[3];
};

}  // namespace WaterConcept
#endif
