#include <stdio.h>
#include <sys/utsname.h>

#define MAX 1024

int
main(int argc, char ** argv)
{
    struct utsname buf;
	int retval = uname(&buf);
//    (void)puts(buf.sysname);
	return retval;
}