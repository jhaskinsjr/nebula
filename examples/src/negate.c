#include <stdio.h>

#include "basics.h"

int
main(int argc, char ** argv)
{
	return -1 * ((argc > 1) ? (int)atoi(argv[1]) : 0);
}
