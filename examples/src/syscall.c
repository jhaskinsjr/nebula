#include <stdio.h>
#include <sys/utsname.h>

#include "basics.h"

int
main(int argc, char ** argv)
{
    struct utsname buf;
	int retval = uname(&buf);
    puts(buf.sysname);
//    put_string(buf.sysname);
//    put_string(buf.nodename);
//    put_string(buf.release);
//    put_string(buf.version);
//    put_string(buf.machine);
	return retval;
}