#include <unistd.h>

int
atoi(const char * s)
{
	int retval = 0;
	int x = ('-' == s[0]) ? 1 : 0;
	while (s[x] >= '0' && s[x] <= '9') {
		retval *= 10;
		retval += s[x] - '0';
		x += 1;
	}
	return (('-' == s[0]) ? 0 - retval : 0 + retval);
}

#define STDOUT_FD (int)1

int
put_string(const char * s)
{
	int x = 0;
	while (s[x]) x += 1;
	asm(
		"\taddi x17, x0, 64\n"
		"\taddi x10, x0, 1\n"
		"\tadd x11, x0, %0\n"
		"\tadd x12, x0, %1\n"
		"\tecall\n"
		:
		: "r" (s), "r" (x)
	);
	return x;
}