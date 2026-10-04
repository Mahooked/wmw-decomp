// Recovered from Walaber::FileManager::FH_ZipFileSystem. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WALABER__FILEMANAGER__FH_ZIPFILESYSTEM_H
#define WMW_WALABER__FILEMANAGER__FH_ZIPFILESYSTEM_H

#include <stdint.h>

namespace Walaber {
namespace FileManager {
struct FH_ZipFileSystem {
    // size 56, align 8, confidence high
    uint64_t f_0x0;
    uint64_t f_0x8;
    uint8_t _pad40[24];
    uint64_t f_0x28;
    uint64_t f_0x30;
};

}  // namespace Walaber::FileManager
#endif
