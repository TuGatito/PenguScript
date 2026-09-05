typedef struct _IO_FILE FILE;
extern FILE* stdin; extern FILE* stdout; extern FILE* stderr;
int printf(const char* fmt, ...); int fprintf(FILE* f, const char* fmt, ...);
int snprintf(char* buf, unsigned long long n, const char* fmt, ...);
int sprintf(char* buf, const char* fmt, ...);
int fflush(FILE* f); int fclose(FILE* f);
void* fopen(const char* p, const char* m);