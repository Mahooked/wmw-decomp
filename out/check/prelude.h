/* prelude.h -- the ambient declarations every libwmw.so body is checked
   against by ``tools/check_syntax.py``.

   The decompiled bodies are compiler output, not source: they name Ghidra's
   primitives (``undefined8``), the ABI's helpers (``__stack_chk_fail``), the
   libc functions the PLT imports resolve to, and the small set of libc++
   templates that appear in recovered signatures.  None of that was ever
   written by hand, and the binary's own headers were never shipped, so the
   ambient layer is declared here rather than included.

   This file is *not* part of the recovered program.  It exists only so that
   ``clang++ -fsyntax-only`` can be pointed at each generated .cpp and asked
   what is structurally wrong with it. */
#pragma once

/* ---- Ghidra / decompiler primitive types ---- */
typedef unsigned char      undefined;
typedef unsigned char      undefined1;
typedef unsigned short     undefined2;
typedef unsigned int       undefined3;
typedef unsigned int       undefined4;
typedef unsigned long long undefined5;
typedef unsigned long long undefined6;
typedef unsigned long long undefined7;
typedef unsigned long long undefined8;
typedef unsigned char      byte;
typedef unsigned char      uchar;
typedef unsigned short     ushort;
typedef unsigned int       uint;
typedef unsigned long long ulong;
typedef unsigned long long ulonglong;
typedef long long          longlong;
typedef signed char        schar;
typedef signed char        int1;
typedef short              int2;
typedef int                int3;
typedef int                int4;
typedef long long          int5;
typedef long long          int6;
typedef long long          int7;
typedef long long          int8;
typedef unsigned char      uint1;
typedef unsigned short     uint2;
typedef unsigned int       uint3;
typedef unsigned int       uint4;
typedef unsigned long long uint5;
typedef unsigned long long uint6;
typedef unsigned long long uint7;
typedef unsigned long long uint8;
struct _Datum;                          /* the data-global placeholder, below */
/* Ghidra's `code` is its function-pointer type; libxml2's callback globals
   are called through it as `(*(code *)xmlMalloc)(n)` or
   `(**(code **)(*p + 0x10))(a, b)`.  As an integer typedef every one of those
   calls is "called object type 'code' is not a function" (3,154 of them), so
   `code` is a class whose call operator takes any arguments and yields a
   `_Datum` -- convertible to, assignable to and indexable by anything, which
   is all the gate needs of a pointer to code that was never recovered. */
struct code { template <class... A> _Datum operator()(A...); };

typedef unsigned char      uint8_t;
typedef unsigned short     uint16_t;
typedef unsigned int       uint32_t;
typedef unsigned long long uint64_t;
typedef signed char        int8_t;
typedef short              int16_t;
typedef int                int32_t;
typedef long long          int64_t;
typedef __SIZE_TYPE__      size_t;
typedef __PTRDIFF_TYPE__   ssize_t;
typedef long double        longdouble;
typedef char16_t           wchar16;
typedef unsigned int       unsigned_int;   /* Ghidra writes this as a type name */
typedef unsigned int       word;
struct tm;
typedef struct { char __opaque[8];  } mbstate_t;
typedef struct { char __opaque[64]; } pthread_mutex_t;
typedef struct { char __opaque[64]; } pthread_cond_t;
typedef struct { char __opaque[8];  } pthread_mutexattr_t;
typedef struct { char __opaque[64]; } pthread_attr_t;
typedef unsigned int  pthread_key_t;
typedef unsigned long pthread_t;

/* libc++ spells the aligned-allocation tag `enum class align_val_t : size_t`.
   Declaring any global operator new/delete (immediately below) makes clang
   pre-declare this implicitly as an enum; the recovered `struct
   align_val_t` is therefore suppressed in decls.h, and _globals.cpp defines
   `operator_delete(void *, size_t, std::align_val_t)` with the parameter by
   value, so declare it here -- complete -- before the operator block. */
namespace std { enum class align_val_t : size_t {}; }

/* ---- allocation: the bodies call operator new/delete by name, and the
   constructor call-site rewrite (`new (obj) T(args)`) needs the placement
   form declared.  Declared, never defined: the gate is syntax-only. ---- */
void *operator new(size_t);
void *operator new[](size_t);
void *operator new(size_t, void *) noexcept;
void operator delete(void *) noexcept;
void operator delete[](void *) noexcept;
void operator delete(void *, void *) noexcept;

/* ---- ABI helpers emitted by the compiler ---- */
extern "C" void __stack_chk_fail(void) __attribute__((noreturn));
extern "C" void __cxa_pure_virtual(void) __attribute__((noreturn));

/* Allocator shims the PLT resolver writes at the call site. */
void *operator_new(unsigned long n);
void  operator_delete(void *p);
void  operator_delete_arr(void *p);

/* Ghidra's sub-register fold helpers (``CONCAT21``, ``SUB81``, ``ZEXT416``,
   ``SEXT816`` ...) are emitted by ``tools/check_syntax.py``: the set and arity
   of the names is a property of the bodies themselves, so the tool scans for
   them and declares each as a variadic template rather than hard-coding a
   list here. */

/* ---- libc (the subset the PLT imports resolve to) ---- */
extern "C" {
void  *malloc(size_t);
void  *calloc(size_t, size_t);
void  *realloc(void *, size_t);
void   free(void *);
void  *memcpy(void *, const void *, size_t);
void  *memmove(void *, const void *, size_t);
void  *memset(void *, int, size_t);
int    memcmp(const void *, const void *, size_t);
size_t strlen(const char *);
char  *strcpy(char *, const char *);
char  *strncpy(char *, const char *, size_t);
char  *strcat(char *, const char *);
char  *strncat(char *, const char *, size_t);
int    strcmp(const char *, const char *);
int    strncmp(const char *, const char *, size_t);
char  *strchr(const char *, int);
char  *strrchr(const char *, int);
char  *strstr(const char *, const char *);
int    printf(const char *, ...);
int    fprintf(void *, const char *, ...);
int    sprintf(char *, const char *, ...);
int    snprintf(char *, size_t, const char *, ...);
int    puts(const char *);
int    fputs(const char *, void *);
int    fputc(int, void *);
void  *fopen(const char *, const char *);
int    fclose(void *);
int    fflush(void *);
size_t fread(void *, size_t, size_t, void *);
size_t fwrite(const void *, size_t, size_t, void *);
int    fseek(void *, long, int);
long   ftell(void *);
void   abort(void) __attribute__((noreturn));
void   exit(int) __attribute__((noreturn));
int    atoi(const char *);
long   atol(const char *);
double strtod(const char *, char **);
double atof(const char *);
int    rand(void);
void   srand(unsigned int);
int    toupper(int);
int    tolower(int);
int    isalpha(int);
int    isdigit(int);
int    isspace(int);
double sqrt(double);
double sin(double);
double cos(double);
double tan(double);
double atan2(double, double);
double fabs(double);
double floor(double);
double ceil(double);
double pow(double, double);
double fmod(double, double);
double exp(double);
double log(double);
double log10(double);
long   lround(double);
/* float variants Ghidra calls by their libm names */
float  sinf(float);
float  cosf(float);
float  tanf(float);
float  sqrtf(float);
float  atan2f(float, float);
float  fabsf(float);
float  powf(float, float);
float  floorf(float);
float  ceilf(float);
float  expf(float);
float  logf(float);
float  fmodf(float, float);
float  fminf(float, float);
float  fmaxf(float, float);
/* further libc the PLT imports resolve to */
int    sscanf(const char *, const char *, ...);
void  *memchr(const void *, int, size_t);
char  *builtin_strncpy(char *, const char *, size_t);   /* Ghidra's name for strncpy */
int    pthread_mutex_lock(pthread_mutex_t *);
int    pthread_mutex_unlock(pthread_mutex_t *);
int    pthread_mutex_trylock(pthread_mutex_t *);
int    pthread_mutex_destroy(pthread_mutex_t *);
int    pthread_mutexattr_init(pthread_mutexattr_t *);
int    pthread_mutexattr_destroy(pthread_mutexattr_t *);
int    pthread_mutexattr_settype(pthread_mutexattr_t *, int);
int    pthread_cond_broadcast(pthread_cond_t *);
int    pthread_cond_signal(pthread_cond_t *);
int    pthread_cond_wait(pthread_cond_t *, pthread_mutex_t *);
int    pthread_cond_timedwait(pthread_cond_t *, pthread_mutex_t *, const void *);
int    pthread_cond_destroy(pthread_cond_t *);
int    pthread_once(void *, void (*)(void));
int    pthread_key_create(pthread_key_t *, void (*)(void *));
void  *pthread_getspecific(pthread_key_t);
int    pthread_setspecific(pthread_key_t, const void *);
pthread_t pthread_self(void);
int    pthread_equal(pthread_t, pthread_t);
int    pthread_join(pthread_t, void **);
int    pthread_detach(pthread_t);
int    __android_log_write(int, const char *, const char *);
int    __android_log_print(int, const char *, const char *, ...);
int    __android_log_vprint(int, const char *, const char *, void *);
int   *__errno(void);
}

/* ---- libc++ skeletons ----
   Recovered signatures reach into libc++ (``basic_string<char, char_traits<char>,
   allocator<char>>``) and the bodies call its members in static form.  The real
   headers were not shipped and these templates are far larger than the handful
   of members the bodies touch, so only the primary templates are declared. */
namespace std {
inline namespace __ndk1 {
template <class T> struct allocator;
template <class T> struct char_traits;
template <class T> struct less;
template <class T> struct hash;
template <class A, class B> struct pair;
template <class... T> struct tuple;
template <class T, class D = T> struct default_delete;
template <class T, class D = default_delete<T>> struct unique_ptr;
template <class T> struct unique_lock;
template <class T> struct lock_guard;
template <class T> struct shared_ptr;
template <class T> struct weak_ptr;
template <class T> struct initializer_list;
template <class T> struct iterator_traits;
template <class T> struct reverse_iterator;
template <class C, class T = char_traits<C>, class A = allocator<C>>
struct basic_string;
template <class T, class A = allocator<T>> struct vector;
template <class T, class A = allocator<T>> struct deque;
template <class T, class A = allocator<T>> struct list;
template <class K, class V, class C = less<K>, class A = allocator<pair<K, V>>>
struct map;
template <class K, class V, class C = less<K>, class A = allocator<pair<K, V>>>
struct multimap;
template <class K, class C = less<K>, class A = allocator<K>> struct set;
template <class T, class C = less<T>, class A = allocator<T>> struct __tree;
template <class K, class V> struct __value_type;
template <class K, class V, class C> struct __map_value_compare;
template <class T, class P> struct __tree_node;
template <class T> struct __tree_node_base;
template <class T> struct __tree_end_node;
template <class T> struct __tree_iterator;
template <class T> struct __tree_const_iterator;
template <class T> struct __tree_node_destructor;
template <class T, class A> struct __split_buffer;
template <class...> struct __deque_base { };
template <class T, class A = allocator<T>> struct __vector_base { template <class... _A> __vector_base(_A...); };
template <class T> struct __vector_base_common;
template <class C, class T = char_traits<C>> struct basic_ostream;
template <class C, class T = char_traits<C>> struct basic_istream;
template <class C, class T = char_traits<C>> struct basic_iostream;
template <class C, class T = char_traits<C>> struct basic_streambuf;
template <class C, class T = char_traits<C>> struct basic_stringbuf;
template <class C, class T = char_traits<C>> struct basic_filebuf { template <class... _A> basic_filebuf(_A...); };
template <class C, class T = char_traits<C>> struct istreambuf_iterator;
template <class C, class T = char_traits<C>> struct ostreambuf_iterator;
template <class C> struct __basic_string_common;
template <class T> struct ctype;
template <class T> struct codecvt;
template <class T> struct moneypunct;
template <class T> struct moneypunct_byname;
template <class T> struct numpunct;
template <class T> struct num_get;
template <class T> struct num_put;
template <class T> struct time_get;
template <class T> struct time_put;
template <class T> struct collate;
template <class T> struct messages;
struct locale;
struct ios_base;
struct __shared_count;
struct __shared_weak_count;
struct piecewise_construct_t;
struct exception;
struct exception_ptr;
struct logic_error;
struct runtime_error;
struct __thread_struct;
}
}

namespace Walaber {
template <class T> struct SharedPtr { template <class... _A> SharedPtr(_A...); };
template <class T> struct MemberCallback { template <class... _A> MemberCallback(_A...); };
template <class T> struct WeakPtr { template <class... _A> WeakPtr(_A...); };
}

/* ---- placeholder for unresolved data symbols ----
   Globals the .so never named (``DAT_00e12345``) are declared as this type, so
   that any of the ways a body touches them -- load, store, take the address,
   index, call through, cast -- still parses. */
struct _Datum {
  _Datum() {}
  template <class T> operator T() const;
  template <class T> _Datum &operator=(T);
  _Datum &operator=(const _Datum &);
  template <class T> _Datum &operator[](T) const;
  long long operator()(...) const;             /* call through a data global */
  _Datum operator*() const;                    /* indirect through one */
  struct _Addr { template <class T> operator T *() const; };
  _Addr operator&() const;
};

/* ---- platform symbols the bodies call by name ----
   libGLESv2, libxml2, NEON helpers, FMOD and the statically linked
   codecs appear in the dynamic table only as bare C names; their real
   signatures were not shipped, so they are declared opaquely.  _Datum
   accepts a call, a value, a subscript or an address, which is all a
   syntax check needs from a symbol it is not going to resolve. */
extern _Datum FMOD_Memory_GetStats;
extern _Datum FMOD_System_Create;
extern _Datum NEON_ext;
extern _Datum NEON_fminnm;
extern _Datum NEON_fmov;
extern _Datum NEON_rev64;
extern _Datum NEON_scvtf;
extern _Datum NEON_smax;
extern _Datum NEON_smin;
extern _Datum NEON_ucvtf;
extern _Datum NEON_ushl;
extern _Datum crc32;
extern _Datum deflate;
extern _Datum deflateEnd;
extern _Datum deflateInit2_;
extern _Datum glActiveTexture;
extern _Datum glBindBuffer;
extern _Datum glBindFramebufferOES;
extern _Datum glBindTexture;
extern _Datum glBlendFunc;
extern _Datum glBufferData;
extern _Datum glBufferSubData;
extern _Datum glCheckFramebufferStatusOES;
extern _Datum glClear;
extern _Datum glClearColor;
extern _Datum glClientActiveTexture;
extern _Datum glColor4f;
extern _Datum glColorMask;
extern _Datum glColorPointer;
extern _Datum glCompressedTexImage2D;
extern _Datum glDeleteBuffers;
extern _Datum glDeleteFramebuffersOES;
extern _Datum glDeleteTextures;
extern _Datum glDepthFunc;
extern _Datum glDisable;
extern _Datum glDisableClientState;
extern _Datum glDrawArrays;
extern _Datum glEnable;
extern _Datum glEnableClientState;
extern _Datum glFinish;
extern _Datum glFramebufferTexture2DOES;
extern _Datum glGenBuffers;
extern _Datum glGenFramebuffersOES;
extern _Datum glGenTextures;
extern _Datum glGetBooleanv;
extern _Datum glGetError;
extern _Datum glGetFloatv;
extern _Datum glGetIntegerv;
extern _Datum glGetPointerv;
extern _Datum glGetString;
extern _Datum glGetTexEnvfv;
extern _Datum glGetTexEnviv;
extern _Datum glLineWidth;
extern _Datum glLoadIdentity;
extern _Datum glLoadMatrixf;
extern _Datum glLogicOp;
extern _Datum glMapBufferOES;
extern _Datum glMatrixMode;
extern _Datum glOrthof;
extern _Datum glPopMatrix;
extern _Datum glPushMatrix;
extern _Datum glReadPixels;
extern _Datum glRotatef;
extern _Datum glScalef;
extern _Datum glTexCoordPointer;
extern _Datum glTexEnvfv;
extern _Datum glTexEnvi;
extern _Datum glTexImage2D;
extern _Datum glTexParameteri;
extern _Datum glTranslatef;
extern _Datum glUnmapBufferOES;
extern _Datum glVertexPointer;
extern _Datum glViewport;
extern _Datum inflate;
extern _Datum inflateEnd;
extern _Datum inflateInit2_;
extern _Datum xmlBufferAllocScheme;
extern _Datum xmlDefaultBufferSize;
extern _Datum xmlDefaultSAXHandler;
extern _Datum xmlDefaultSAXLocator;
extern _Datum xmlDeregisterNodeDefaultValue;
extern _Datum xmlDoValidityCheckingDefaultValue;
extern _Datum xmlFree;
extern _Datum xmlGenericError;
extern _Datum xmlGenericErrorContext;
extern _Datum xmlGetWarningsDefaultValue;
extern _Datum xmlIndentTreeOutput;
extern _Datum xmlIsBaseCharGroup;
extern _Datum xmlIsCombiningGroup;
extern _Datum xmlIsDigitGroup;
extern _Datum xmlIsExtenderGroup;
extern _Datum xmlIsPubidChar_tab;
extern _Datum xmlKeepBlanksDefaultValue;
extern _Datum xmlLastError;
extern _Datum xmlLineNumbersDefaultValue;
extern _Datum xmlLoadExtDtdDefaultValue;
extern _Datum xmlMalloc;
extern _Datum xmlMallocAtomic;
extern _Datum xmlMemStrdup;
extern _Datum xmlOutputBufferCreateFilenameValue;
extern _Datum xmlParserDebugEntities;
extern _Datum xmlParserInputBufferCreateFilenameValue;
extern _Datum xmlParserMaxDepth;
extern _Datum xmlParserVersion;
extern _Datum xmlPedanticParserDefaultValue;
extern _Datum xmlRealloc;
extern _Datum xmlRegisterNodeDefaultValue;
extern _Datum xmlSaveNoEmptyTags;
extern _Datum xmlStringText;
extern _Datum xmlStructuredError;
extern _Datum xmlSubstituteEntitiesDefaultValue;
extern _Datum xmlTreeIndentString;
extern _Datum xmlXPathCastNodeSetToNumber;
extern _Datum xmlXPathCastToNumber;
extern _Datum xmlXPathNAN;
extern _Datum xmlXPathNINF;
extern _Datum xmlXPathStringEvalNumber;
