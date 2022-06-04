#include <stdio.h>

#include "basics.h"

int
main(int argc, char ** argv)
{
	int retval = 0;
	int x = 1;
	for (; x < argc; x += 1) retval += atoi(argv[x]);
	return retval;
}
