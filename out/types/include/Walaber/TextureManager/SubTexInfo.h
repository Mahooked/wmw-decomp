// Recovered from Walaber::TextureManager::SubTexInfo. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WALABER__TEXTUREMANAGER__SUBTEXINFO_H
#define WMW_WALABER__TEXTUREMANAGER__SUBTEXINFO_H

#include <stdint.h>

namespace Walaber {
namespace TextureManager {
struct SubTexInfo {
    // size 64, align 16, confidence med
    uint8_t _pad24[24];
    uint64_t f_0x18;
    uint8_t _pad40[8];
    uint64_t f_0x28;
    uint64_t f_0x30;
    int32_t f_0x38;
    uint8_t _tail[4];
};

}  // namespace Walaber::TextureManager
#endif
