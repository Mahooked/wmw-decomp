// Recovered from Walaber::FileManager::ReadFileCallbackParameters. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WALABER__FILEMANAGER__READFILECALLBACKPARAMETERS_H
#define WMW_WALABER__FILEMANAGER__READFILECALLBACKPARAMETERS_H

#include <stdint.h>

namespace Walaber {
namespace FileManager {
struct ReadFileCallbackParameters {
    // size 48, align 8, confidence high
    uint8_t _pad32[32];
    uint64_t f_0x20;
    uint64_t f_0x28;
};

}  // namespace Walaber::FileManager
#endif
